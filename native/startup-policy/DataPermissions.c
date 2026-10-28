// SPDX-License-Identifier: BSD-2-Clause-Patent
// Restore numeric template metadata on this boot's verified volatile Data only.
// No file creation/content changes, account records, keys or OS writes.
#include <sys/param.h>
#include <sys/systm.h>
#include <sys/proc.h>
#include <sys/sysproto.h>
#include <sys/fcntl.h>
#include <sys/stat.h>
#include <pexpert/pexpert.h>
#include "DataPermissions.h"

extern int zorn_ufs_boot_policy_allowed(void);
extern void zorn_say(const char *);
volatile unsigned zorn_data_permissions_stage, zorn_data_permissions_checked, zorn_data_permissions_total;
volatile unsigned zorn_data_permissions_root_uid=~0U, zorn_data_permissions_root_gid=~0U;
volatile int zorn_data_permissions_status=-1;

__attribute__((noinline)) int zorn_boot_data_permissions(void *process, uint64_t scratch)
{
    int enabled=0, error=0;
    PE_parse_boot_argn("zorn_data_permissions", &enabled, sizeof(enabled));
    if (enabled != 1) return 0;
    zorn_data_permissions_stage=1;
    zorn_data_permissions_total=sizeof(zorn_data_permission_specs)/sizeof(zorn_data_permission_specs[0]);
    if (!zorn_ufs_boot_policy_allowed()) { error=EPERM; goto done; }
    int retained=0;
    PE_parse_boot_argn("zorn_data_retained",&retained,sizeof(retained));
    if(retained) {
        extern int zorn_boot_data_marker_existing(void *,uint64_t);
        if(retained!=1){error=EINVAL;goto done;}
        error=zorn_boot_data_marker_existing(process,scratch);
        if(!error) {
            // First-boot seed entries (e.g. containers/Temp) can legitimately
            // disappear during OS initialization. Do not restore that template.
            zorn_data_permissions_stage=4;
            zorn_data_permissions_root_uid=0;zorn_data_permissions_root_gid=0;
        }
        goto done;
    }
    proc_t p=process;
    dev_t root_device=0;
    zorn_data_permissions_stage=2;
    for (unsigned index=0; index<zorn_data_permissions_total; ++index) {
        const struct ZornDataPermissionSpec *entry=&zorn_data_permission_specs[index];
        struct stat64 st={0};
        int fd=-1;
        int32_t result=0;
        if ((error=copyout(entry->path,scratch,strlen(entry->path)+1))) goto item_done;
        struct open_args op={.path=scratch,.flags=O_RDONLY|O_NOFOLLOW|(entry->type==S_IFDIR?O_DIRECTORY:0),.mode=0};
        if ((error=open(p,&op,&result))) goto item_done;
        fd=result;
        struct fstat64_args sa={.fd=fd,.ub=scratch+0x800};
        if ((error=sys_fstat64(p,&sa,&result)) || (error=copyin(sa.ub,&st,sizeof(st)))) goto item_done;
        if ((st.st_mode&S_IFMT)!=entry->type) { error=EINVAL; goto item_done; }
        if (!index) root_device=st.st_dev;
        if (st.st_dev!=root_device) { error=EXDEV; goto item_done; }
        struct fchown_args owner={.fd=fd,.uid=entry->uid,.gid=entry->gid};
        if ((error=fchown(p,&owner,&result))) goto item_done;
        struct fchmod_args mode={.fd=fd,.mode=entry->mode};
        if ((error=fchmod(p,&mode,&result))) goto item_done;
        if ((error=sys_fstat64(p,&sa,&result)) || (error=copyin(sa.ub,&st,sizeof(st)))) goto item_done;
        if (st.st_dev!=root_device || (st.st_mode&S_IFMT)!=entry->type ||
            st.st_uid!=entry->uid || st.st_gid!=entry->gid || (st.st_mode&07777)!=entry->mode) {
            error=EINVAL; goto item_done;
        }
        if (!index) { zorn_data_permissions_root_uid=st.st_uid; zorn_data_permissions_root_gid=st.st_gid; }
item_done:
        if (fd>=0) { struct close_args cl={.fd=fd}; int close_error=sys_close(p,&cl,&result); if (!error) error=close_error; }
        if (error) {
            printf("zorn Data metadata: error=%d index=%u path=%s\n",error,index,entry->path);
            break;
        }
        ++zorn_data_permissions_checked;
    }
    if (!error) zorn_data_permissions_stage=3;
done:
    zorn_data_permissions_status=error;
    zorn_say(error?"DPOWNFAIL":zorn_data_permissions_stage==4?"DPOWNKEEP":"DPOWNOK");
    printf("zorn Data metadata: stage=%u error=%d checked=%u/%u root=%u:%u (volatile only)\n",
        zorn_data_permissions_stage,error,zorn_data_permissions_checked,zorn_data_permissions_total,
        zorn_data_permissions_root_uid,zorn_data_permissions_root_gid);
    return error;
}
