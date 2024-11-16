#include "debug/debug_macros.h"
#include "debug/debug_print.h"
#include "globals/assert.h"
#include "bp/bp.param.h"

#include "tatp_hash.h"

#include <vector>
#include "../libs/hash_lib.h"

#define HHRT_HISTORY_BITS 12                             // Same as AHRT_HISTORY_BITS
#define HPT_ENTRIES (1 << HHRT_HISTORY_BITS)
#define PHT_CTR_BITS 2

#define ASSOCIATIVITY TATP_ASSOC                         // 4-way

#define DEFAULT_HRT_VALUE N_BIT_MASK(HHRT_HISTORY_BITS)

#define DEBUG_ON 0

struct HHRT_Entry {
    uint32_t history;                                    // 12-bit history
};

struct HHRT_State {
    Hash_Table hhrt;           // Hash table for HHRT
    std::vector<uint32_t> HPT; // History Pattern Table
};

HHRT_State hhrt_state;

void bp_hhrt_timestamp(Op* op) {}
void bp_hhrt_recover(Recovery_Info* info) {}
void bp_hhrt_spec_update(Op* op) {}
void bp_hhrt_retire(Op* op) {}
uns8 bp_hhrt_full(uns proc_id) { return 0; }

void bp_hhrt_init() {
    // hash table, collision policy: chaining(bucket size is 4(4-way))
    init_hash_table(&hhrt_state.hhrt, "HHRT Hash Table", ASSOCIATIVITY, sizeof(HHRT_Entry));
    
    // Initialize HPT with weakly taken (binary 10)
    hhrt_state.HPT.resize(HPT_ENTRIES, N_BIT_MASK(PHT_CTR_BITS));
}

uns8 bp_hhrt_pred(Op* op) {
#if DEBUG_ON
    DPRINTF("HHRT_PRED: Predicting for address: %llx\n", op->oracle_info.pred_addr);
#endif

    int64 key = op->oracle_info.pred_addr;
    HHRT_Entry* entry = (HHRT_Entry*)hash_table_access(&hhrt_state.hhrt, key);

    uint32_t hpt_index;
    if (entry) {
        hpt_index = entry->history;
    } else {
        hpt_index = DEFAULT_HRT_VALUE;
    }

    uint32_t hpt_entry = hhrt_state.HPT[hpt_index];
    int pred = (hpt_entry >> (PHT_CTR_BITS - 1)) & 0x1;

    return pred;
}

void bp_hhrt_update(Op* op) {
    if (op->table_info->cf_type != CF_CBR) {
        return;
    }
    
    int64 key = op->oracle_info.pred_addr;
    Flag new_entry = FALSE;
    HHRT_Entry* entry = (HHRT_Entry*)hash_table_access_create(&hhrt_state.hhrt, key, &new_entry);
    
    if (new_entry) {
        entry->history = DEFAULT_HRT_VALUE;
    }
    
    uint32_t hpt_index = entry->history;
    
    if (op->oracle_info.dir) {
        hhrt_state.HPT[hpt_index] = SAT_INC(hhrt_state.HPT[hpt_index], N_BIT_MASK(PHT_CTR_BITS));
    } else {
        hhrt_state.HPT[hpt_index] = SAT_DEC(hhrt_state.HPT[hpt_index], 0);
    }
    
    entry->history = ((entry->history << 1) & N_BIT_MASK(HHRT_HISTORY_BITS)) | (op->oracle_info.dir ? 1 : 0);
}
