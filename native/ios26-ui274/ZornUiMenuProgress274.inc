// SPDX-License-Identifier: BSD-2-Clause-Patent
// Read actual existing CPU snapshots only. No GPU MMIO,command,reset,wait,
// backend callback substitute or resource-release authority is introduced.
extern "C" void zorn26_ui_menu_progress274(uint32_t (&out)[16]){
    for(auto &v:out)v=0;
    uint32_t p[16]{};
    if(zorn26_present_snapshot245(p)){
        out[0]|=1;out[1]=p[1];out[2]=p[2];out[3]=p[5];out[4]=p[15];out[5]=p[7];
    }
    ZornClientFailure261 client{};
    // Phase0 prioritizes the actual first backend failure over a capability
    // reject. All-client admission remains the independent full272predicate.
    if(zorn_failure_snapshot261(0,&client)){
        out[0]|=2;out[6]=client.dropped;out[7]=client.failure.sequence;
        out[8]=client.failure.stage;out[9]=client.failure.raw;out[10]=uint32_t(client.id);
        out[11]=client.flags;
    }
    ZornApplicationObservation26 app{};
    if(zorn26_application_snapshot(&app)){
        out[0]|=4;out[12]=app.dropped;out[13]=app.calls;out[14]=uint32_t(app.unique);out[15]=app.pid;
    }
}
