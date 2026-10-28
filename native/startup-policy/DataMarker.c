// SPDX-License-Identifier: BSD-2-Clause-Patent
// Create once and subsequently read back an ordinary file on verified Data.
// Existing contents are never truncated, replaced or silently repaired.
#include <sys/param.h>
#include <sys/systm.h>
#include <sys/proc.h>
#include <sys/sysproto.h>
#include <sys/fcntl.h>
#include <sys/stat.h>
#include <kern/clock.h>
extern unsigned native_ufs_store_mode(void);
extern int zorn_ufs_boot_policy_allowed(void);
extern const unsigned char zorn_data_expected_seed[32];
volatile unsigned zorn_data_marker_state;
volatile int zorn_data_marker_error;
volatile uint64_t zorn_data_marker_cookie;

// Explicit retained-Data boots may only verify an existing initialization
// marker. Missing/foreign/invalid contents fail; this path never creates one.
__attribute__((noinline)) int zorn_boot_data_marker_existing(void *process, uint64_t scratch)
{
    proc_t p=process;int error=0,fd=-1;int32_t result=0;
    struct stat64 st={0};dev_t device=0;unsigned char verify[48]={0};
    if(native_ufs_store_mode()!=2 || !zorn_ufs_boot_policy_allowed()){error=EPERM;goto done;}
    if((error=copyout("/private/var",scratch,13)))goto done;
    struct open_args root={.path=scratch,.flags=O_RDONLY|O_DIRECTORY|O_NOFOLLOW,.mode=0};
    if((error=open(p,&root,&result)))goto done;
    fd=result;
    struct fstat64_args sa={.fd=fd,.ub=scratch+0x800};
    if((error=sys_fstat64(p,&sa,&result)) || (error=copyin(sa.ub,&st,sizeof(st))))goto done;
    if(!S_ISDIR(st.st_mode) || st.st_uid || st.st_gid || (st.st_mode&07777)!=0755){error=EINVAL;goto done;}
    device=st.st_dev;
    {struct close_args cl={.fd=fd};error=sys_close(p,&cl,&result);fd=-1;if(error)goto done;}
    const char *path="/private/var/db/.unixnu-data-retained";
    if((error=copyout(path,scratch,strlen(path)+1)))goto done;
    struct open_args ro={.path=scratch,.flags=O_RDONLY|O_NOFOLLOW,.mode=0};
    if((error=open(p,&ro,&result)))goto done;
    fd=result;sa.fd=fd;
    if((error=sys_fstat64(p,&sa,&result)) || (error=copyin(sa.ub,&st,sizeof(st))))goto done;
    if(st.st_dev!=device || !S_ISREG(st.st_mode) || st.st_uid || st.st_gid ||
       (st.st_mode&07777)!=0600 || st.st_size!=(off_t)sizeof(verify)){error=EINVAL;goto done;}
    struct read_args rd={.fd=fd,.cbuf=scratch+0x200,.nbyte=sizeof(verify)};user_ssize_t got=0;
    if((error=read(p,&rd,&got)) || (error=copyin(scratch+0x200,verify,sizeof(verify))))goto done;
    if(got!=(user_ssize_t)sizeof(verify) || memcmp(verify,"ZRNKEEP1",8) ||
       memcmp(verify+8,zorn_data_expected_seed,32)){error=EIO;goto done;}
    memcpy((void *)&zorn_data_marker_cookie,verify+40,8);
    if(!zorn_data_marker_cookie){error=EINVAL;goto done;}
done:
    if(fd>=0){struct close_args cl={.fd=fd};int e=sys_close(p,&cl,&result);if(!error)error=e;}
    zorn_data_marker_error=error;zorn_data_marker_state=error?3:2;
    return error;
}

int zorn_boot_data_marker(void *process, uint64_t scratch)
{
    if (native_ufs_store_mode() != 2) return 0;
    proc_t p=process;
    int error=0,fd=-1,created=0;int32_t result=0;
    unsigned char payload[48]={0},verify[48]={0};
    struct stat64 st={0};dev_t device=0;
    const char *path="/private/var/db/.unixnu-data-retained";
    if(!zorn_ufs_boot_policy_allowed()){error=EPERM;goto done;}
    if((error=copyout("/private/var",scratch,13)))goto done;
    struct open_args root={.path=scratch,.flags=O_RDONLY|O_DIRECTORY|O_NOFOLLOW,.mode=0};
    if((error=open(p,&root,&result)))goto done;
    fd=result;
    struct fstat64_args sa={.fd=fd,.ub=scratch+0x800};
    if((error=sys_fstat64(p,&sa,&result)) || (error=copyin(sa.ub,&st,sizeof(st))))goto done;
    device=st.st_dev;
    {struct close_args cl={.fd=fd};error=sys_close(p,&cl,&result);fd=-1;if(error)goto done;}
    if((error=copyout(path,scratch,strlen(path)+1)))goto done;
    struct open_args op={.path=scratch,.flags=O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,.mode=0600};
    error=open(p,&op,&result);
    if(!error){
        fd=result;created=1;
        memcpy(payload,"ZRNKEEP1",8);memcpy(payload+8,zorn_data_expected_seed,32);
        uint64_t cookie=mach_absolute_time();memcpy(payload+40,&cookie,8);
        if((error=copyout(payload,scratch+0x200,sizeof(payload))))goto done;
        struct write_args wr={.fd=fd,.cbuf=scratch+0x200,.nbyte=sizeof(payload)};
        user_ssize_t written=0;
        if((error=write(p,&wr,&written)))goto done;
        if(written!=(user_ssize_t)sizeof(payload)){error=EIO;goto done;}
        struct fchown_args owner={.fd=fd,.uid=0,.gid=0};
        struct fchmod_args mode={.fd=fd,.mode=0600};
        struct fsync_args sync={.fd=fd};
        if((error=fchown(p,&owner,&result)) || (error=fchmod(p,&mode,&result)) || (error=fsync(p,&sync,&result)))goto done;
        struct close_args cl={.fd=fd};error=sys_close(p,&cl,&result);fd=-1;if(error)goto done;
    }else if(error==EEXIST)error=0;else goto done;
    struct open_args ro={.path=scratch,.flags=O_RDONLY|O_NOFOLLOW,.mode=0};
    if((error=open(p,&ro,&result)))goto done;
    fd=result;sa.fd=fd;
    if((error=sys_fstat64(p,&sa,&result)) || (error=copyin(sa.ub,&st,sizeof(st))))goto done;
    if(st.st_dev!=device || !S_ISREG(st.st_mode) || st.st_uid || st.st_gid ||
       (st.st_mode&07777)!=0600 || st.st_size!=(off_t)sizeof(verify)){error=EINVAL;goto done;}
    struct read_args rd={.fd=fd,.cbuf=scratch+0x200,.nbyte=sizeof(verify)};user_ssize_t got=0;
    if((error=read(p,&rd,&got)) || (error=copyin(scratch+0x200,verify,sizeof(verify))))goto done;
    if(got!=(user_ssize_t)sizeof(verify) || memcmp(verify,"ZRNKEEP1",8) || memcmp(verify+8,zorn_data_expected_seed,32) ||
       (created && memcmp(payload,verify,sizeof(payload)))){error=EIO;goto done;}
    uint64_t saved_cookie=0;memcpy(&saved_cookie,verify+40,8);zorn_data_marker_cookie=saved_cookie;
    if(!zorn_data_marker_cookie){error=EINVAL;goto done;}
done:
    if(fd>=0){struct close_args cl={.fd=fd};int e=sys_close(p,&cl,&result);if(!error)error=e;}
    zorn_data_marker_error=error;
    zorn_data_marker_state=error?3:created?1:2;
    return error;
}
