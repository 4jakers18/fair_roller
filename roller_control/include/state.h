// include/state.h
#pragma once

enum RunState {
  DISCONNECTED,
  CONNECTED,
  VERIFY_DIE,
  SPINNING,
  PAUSED,
  FINISHED
};
extern bool finishedSent;
extern RunState state;

extern int  seq;         // current roll index
extern int  totalRolls;  // target # of rolls (from server)
