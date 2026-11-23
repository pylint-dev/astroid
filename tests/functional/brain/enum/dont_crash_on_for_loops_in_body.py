class Commands(IntEnum):
    _ignore_ = 'Commands index'
    _init_ = 'value string'

    BEL = 0x07, 'Bell'
    Commands = vars()
    for index in range(4):
        Commands[f'DC{index + 1}'] = 0x11 + index, f'Device Control {index + 1}'

Commands  # inferred: ClassDef(dont_crash_on_for_loops_in_body.Commands)
