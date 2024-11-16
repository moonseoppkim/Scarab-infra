#ifndef __TATP_HASH_H__
#define __TATP_HASH_H__

#ifdef __cplusplus
extern "C" {
#endif

#include "bp/bp.h" // Include Scarab's branch predictor interface

/************* Interface to Scarab ***************/
void bp_hhrt_init(void);
void bp_hhrt_timestamp(Op*);
uns8 bp_hhrt_pred(Op*);
void bp_hhrt_spec_update(Op*);
void bp_hhrt_update(Op*);
void bp_hhrt_retire(Op*);
void bp_hhrt_recover(Recovery_Info*);
uns8 bp_hhrt_full(uns);

#ifdef __cplusplus
}
#endif

#endif  // __TATP_HASH_H__
