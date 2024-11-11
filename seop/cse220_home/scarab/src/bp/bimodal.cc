#include "bimodal.h"

#include <vector>

extern "C" {
#include "bp/bp.param.h"
#include "core.param.h"
#include "globals/assert.h"
#include "statistics.h"
}

//pht_ctr_bits 2
//00 (strongly not taken)
//01 (weakly not taken)
//10 (weakly taken)
//11 (strongly taken)

//Predict History Table CounTeR Bits
#define PHT_INIT_VALUE (0x1 << (PHT_CTR_BITS - 1)) /* weakly taken */
#define DEBUG(proc_id, args...) _DEBUG(proc_id, DEBUG_BP_DIR, ##args)

// 2^14(16,384) indecies
#define BIMODAL_INDEX_BITS 14  // 16K entries

namespace {

struct Bimodal_State {
  std::vector<uns8> pht;
};

std::vector<Bimodal_State> bimodal_state_all_cores;

uns32 get_pht_index(const Addr addr) {
  // RV32I/RV64I have a same operation address as 4byte.
  // Therefore, the last 2 bits are always meaningless.
  // ex) 0x04, (0 0100)
  //     0x08, (0 1000)
  //     0x12, (0 1100)
  //     0x16, (1 0000)
  return (addr >> 2) & N_BIT_MASK(BIMODAL_INDEX_BITS);
}

}  // namespace

// Don't know why
void bp_bimodal_timestamp(Op* op) {}
void bp_bimodal_recover(Recovery_Info* info) {}
void bp_bimodal_spec_update(Op* op) {}
void bp_bimodal_retire(Op* op) {}
uns8 bp_bimodal_full(uns proc_id) { return 0; }

void bp_bimodal_init() {
  bimodal_state_all_cores.resize(NUM_CORES);
  for (auto& bimodal_state : bimodal_state_all_cores) {
    // init value: 10 (weakly taken)
    bimodal_state.pht.resize(1 << BIMODAL_INDEX_BITS, PHT_INIT_VALUE);
  }
}

uns8 bp_bimodal_pred(Op* op) {
  const uns   proc_id       = op->proc_id;
  const auto& bimodal_state = bimodal_state_all_cores.at(proc_id);

  const Addr  addr      = op->oracle_info.pred_addr;
  const uns32 pht_index = get_pht_index(addr);
  const uns8  pht_entry = bimodal_state.pht[pht_index];
  const uns8  pred      = (pht_entry >> (PHT_CTR_BITS - 1)) & 0x1;

  DEBUG(proc_id, "Predicting with bimodal for op_num:%s index:%u\n",
        unsstr64(op->op_num), pht_index);
  DEBUG(proc_id, "Predicting addr:%s pht_index:%u pred:%d actual_dir:%d\n",
        hexstr64s(addr), pht_index, pred, op->oracle_info.dir);

  return pred;
}

void bp_bimodal_update(Op* op) {
  if (op->table_info->cf_type != CF_CBR) {
    // Either taken or not taken are the matter of bimodal branch predictor
    return;
  }

  const uns   proc_id       = op->proc_id;
  auto&       bimodal_state = bimodal_state_all_cores.at(proc_id);
  const Addr  addr          = op->oracle_info.pred_addr;
  const uns32 pht_index     = get_pht_index(addr);
  const uns8  pht_entry     = bimodal_state.pht[pht_index];

  DEBUG(proc_id, "Updating bimodal PHT for op_num:%s index:%u dir:%d\n",
        unsstr64(op->op_num), pht_index, op->oracle_info.dir);

  // dir: true direction of branch, set by oracle
  // SAT_INC(val, max) ((val) == (max) ? (max) : (val) + 1)
  // plus one up to max(11)
  //
  // SAT_DEC(val, min) ((val) == (min) ? (min) : (val) - 1)
  // minus one up to min(00)
  if (op->oracle_info.dir) {
    bimodal_state.pht[pht_index] = SAT_INC(pht_entry, N_BIT_MASK(PHT_CTR_BITS));
  } else {
    bimodal_state.pht[pht_index] = SAT_DEC(pht_entry, 0);
  }

  DEBUG(proc_id, "Updated addr:%s pht_index:%u new_entry:%u dir:%d\n",
        hexstr64s(addr), pht_index, bimodal_state.pht[pht_index], op->oracle_info.dir);
}
