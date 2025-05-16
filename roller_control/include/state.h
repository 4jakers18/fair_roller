#pragma once

enum RunState {
  DISCONNECTED,
  CONNECTED,
  VERIFY_DIE,
  SPINNING,
  PAUSED,
  FINISHED
};

extern RunState state;
