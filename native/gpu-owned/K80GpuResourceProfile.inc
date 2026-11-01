/* Fixed cached FDT descriptions; NO mapping/access permission. */
struct K80Resource {const char *name;uint64_t base,bytes;};
static const K80Resource k80Resources[]={
 {"kgsl_3d0_reg_memory",0x3d00000,0x40000},
 {"cx_dbgc",0x3d61000,0x3000},
 {"rscc",0x3d50000,0x10000},
 {"cx_misc",0x3d9e000,0x2000},
 {"qdss_gfx",0x10900000,0x80000},
 {"qdss_etr",0x10048000,0x8000},
 {"qdss_tmc",0x10b05000,0x1000},
 {"gmu",0x3d68000,0x37000},
 {"gmu_pdc",0xb280000,0x10000},
 {"gmu_ao_blk_dec0",0x3d40000,0x10000}
};
static_assert(sizeof(k80Resources)/sizeof(*k80Resources)==ZGN_RESOURCES);
