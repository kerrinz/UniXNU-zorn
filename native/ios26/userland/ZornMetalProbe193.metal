// SPDX-License-Identifier: MIT
// Authored source, compiled only by the official Apple Metal compiler.
#include <metal_stdlib>
using namespace metal;
struct VertexOut { float4 position [[position]]; };
vertex VertexOut zorn193_vertex(uint id [[vertex_id]]) {
 const float2 positions[3]={float2(-1.0,-1.0),float2(3.0,-1.0),float2(-1.0,3.0)};
 VertexOut out; out.position=float4(positions[id],0.0,1.0);return out;
}
fragment float4 zorn193_fragment(VertexOut in [[stage_in]]) {
 const uint cell=((uint(in.position.x)>>3)^(uint(in.position.y)>>3))&1u;
 return cell ? float4(1.0,0.0,1.0,1.0) : float4(0.0,1.0,0.0,1.0);
}
