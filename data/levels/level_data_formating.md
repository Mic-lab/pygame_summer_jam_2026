- in general, a data entry should resemble -> tile_pos>>data_type>>data
- a specific data type decoder should be specified within LEVEL_DATA_PARSER_DISPATCH in level.py
- data entries (if necessary) should be seperated by a single slash (/)

DATA ENTRY TYPES:
- bow (b): x,y -> the direction to shoot in
- spikes (^): state/x,y/... -> the first entry is the default state, while subsequent entries are pressure plates (there is no type check for this) that must be stepped on to trigger the spikes