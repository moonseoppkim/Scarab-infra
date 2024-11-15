#ifndef __TATP_H__
#define __TATP_H__

#ifdef __cplusplus
extern "C" {
#endif

#include "bp/bp.h"

/************* Interface to Scarab ***************/
void bp_tatp_init(void);
void bp_tatp_timestamp(Op*);
uns8 bp_tatp_pred(Op*);
void bp_tatp_spec_update(Op*);
void bp_tatp_update(Op*);
void bp_tatp_retire(Op*);
void bp_tatp_recover(Recovery_Info*);
uns8 bp_tatp_full(uns);

#ifdef __cplusplus
}
#endif

#endif  // __TATP_H__
