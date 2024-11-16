#include "debug/debug_macros.h"
#include "debug/debug_print.h"
#include "globals/assert.h"
#include "bp/bp.param.h"

#include "tatp.h"

#include <vector>
#include <array>
#include <climits>

#define AHRT_TAG_BITS 4
#define AHRT_INDEX_BITS AHRT_INDEX           // parameter1

#define AHRT_ENTRIES (1 << AHRT_INDEX_BITS)  // 2^AHRT_INDEX_BITS entries for AHRT
#define AHRT_HISTORY_BITS 12                 // paremeter2

#define HPT_ENTRIES (1 << AHRT_HISTORY_BITS) // 4096 entries for HPT
#define PHT_CTR_BITS 2                       // 2-bit pattern counter

#define ASSOCIATIVITY TATP_ASSOC             // 4-way

#define DEFAULT_HRT_VALUE N_BIT_MASK(AHRT_HISTORY_BITS)

#define DEBUG_ON 0

struct AHRT_Entry {
    uint32_t tag;         // 2-bit tag
    uint32_t history;     // 12-bit history
    bool valid;           // Valid bit for the entry
    uns64 last_used;      // LRU: Least used cycle
};

// TATP State Structure
struct TATP_State {
    std::vector<std::vector<AHRT_Entry>> AHRT; // 2^index indices, each with 4-way associative AHRT
    std::vector<uint32_t> HPT;                               // History Pattern Table
    
    TATP_State(int entry_count) : AHRT(entry_count), HPT() {}
};

TATP_State tatp_state(AHRT_ENTRIES);

void bp_tatp_timestamp(Op* op) {}
void bp_tatp_recover(Recovery_Info* info) {}
void bp_tatp_spec_update(Op* op) {}
void bp_tatp_retire(Op* op) {}
uns8 bp_tatp_full(uns proc_id) { return 0; }

void bp_tatp_init() {
#if DEBUG_ON
    DPRINTF("SEOP : AHRT_ENTRIES : %d\n", AHRT_ENTRIES);
#endif
    for (auto &index : tatp_state.AHRT) {
        index.resize(ASSOCIATIVITY);
        for (auto &entry : index) {
            entry.tag = 0;
            entry.history = DEFAULT_HRT_VALUE;
            entry.valid = false;
            entry.last_used = 0;
        }
    }

    // Initialize HPT with weakly taken (binary 10)
    tatp_state.HPT.resize(HPT_ENTRIES, N_BIT_MASK(PHT_CTR_BITS));
}

void get_ahrt_index_tag(uint32_t addr, uint32_t& index, uint32_t& tag) {
    // addr : 0x7fff f31a(tag) 5ac4(index)
    //        0x7fff f315(tag) a321(index)
    tag = (addr >> (AHRT_INDEX_BITS + 2)) & N_BIT_MASK(AHRT_TAG_BITS);
    index = (addr >> 2) & N_BIT_MASK(AHRT_INDEX_BITS);
}

#if DEBUG_ON
int seop = 0;
#endif

uns8 bp_tatp_pred(Op* op) {
#if DEBUG_ON
    if (seop++ >= 10000) {
        ASSERT(0, 0);
    }
#endif

    uint32_t index = 0, tag = 0;
    get_ahrt_index_tag(op->oracle_info.pred_addr, index, tag);
#if DEBUG_ON
    DPRINTF("SEOP : try pred_addr : %llx\n", op->oracle_info.pred_addr);
    DPRINTF("SEOP : tag/index : %d / %d\n", tag, index);
#endif

    for (auto &entry : tatp_state.AHRT[index]) {
        if (entry.valid && entry.tag == tag) {
            uint32_t hpt_index = entry.history;
            uint32_t hpt_entry = tatp_state.HPT[hpt_index];
            int pred = (hpt_entry >> (PHT_CTR_BITS - 1)) & 0x1;
            entry.last_used = cycle_count;

#if DEBUG_ON
            DPRINTF("SEOP : cycle_count : %lld\n", cycle_count);
            DPRINTF("SEOP : pred : %d\n", pred);
#endif
            return pred;
        }
    }
    
#if DEBUG_ON
    DPRINTF("SEOP : entry tag not found\n");
#endif
    uint32_t default_history = DEFAULT_HRT_VALUE;
    uint32_t hpt_entry = tatp_state.HPT[default_history];
    int pred = (hpt_entry >> (PHT_CTR_BITS - 1)) & 0x1;
    
    return pred;
}

void bp_tatp_update(Op* op) {
    if (op->table_info->cf_type != CF_CBR) {
        return;
    }

    uint32_t index = 0, tag = 0;
    get_ahrt_index_tag(op->oracle_info.pred_addr, index, tag);

    bool entry_found = false;
    int lru_index = std::rand() % ASSOCIATIVITY; //?
    uns64 oldest_time = UINT64_MAX;

    for (int i = 0; i < ASSOCIATIVITY; i++) {
        auto &entry = tatp_state.AHRT[index][i];
        if (entry.valid && entry.tag == tag) {
            entry_found = true;
            STAT_EVENT(op->proc_id, BP_TATP_HIT);

            uint32_t hpt_index = entry.history;

            // Automaton A2
            if (op->oracle_info.dir) {
                tatp_state.HPT[hpt_index] = SAT_INC(tatp_state.HPT[hpt_index], N_BIT_MASK(PHT_CTR_BITS));
            } else {
                tatp_state.HPT[hpt_index] = SAT_DEC(tatp_state.HPT[hpt_index], 0);
            }

#if DEBUG_ON
            DPRINTF("SEOP : op->oracle_info.dir : %d\n", op->oracle_info.dir);
            DPRINTF("SEOP : prev entry.history : %d\n", entry.history);
#endif
            entry.history = ((entry.history << 1) & N_BIT_MASK(AHRT_HISTORY_BITS)) | (op->oracle_info.dir ? 1 : 0);
#if DEBUG_ON
            DPRINTF("SEOP : after entry.history : %d\n", entry.history);
#endif      
            entry.last_used = cycle_count;
            break;
        }

        if (entry.valid && (entry.last_used < oldest_time)) {
            oldest_time = entry.last_used;
            lru_index = i;
        }
    }

    if (!entry_found) {
        STAT_EVENT(op->proc_id, BP_TATP_MISS);

        for (int i = 0; i < ASSOCIATIVITY; i++) {
            auto &entry = tatp_state.AHRT[index][i];
            if (!entry.valid) {
                entry.valid = true;
                entry.tag = tag;
                entry.history = DEFAULT_HRT_VALUE;
                entry.last_used = cycle_count;
                return;
            }
        }

        if (0 <= lru_index && lru_index < ASSOCIATIVITY) {
            auto &lru_entry = tatp_state.AHRT[index][lru_index];
            lru_entry.valid = true; 
            lru_entry.tag = tag;
            lru_entry.history = DEFAULT_HRT_VALUE;
            lru_entry.last_used = cycle_count;
        } else {
            DPRINTF("SEOP : invalid lru_index : %d", lru_index);
            ASSERT(0, 0);
        }
    }
}
