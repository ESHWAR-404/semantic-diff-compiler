; EVAL-08: After — Struct-of-Arrays layout enables vectorization

define void @update_particles_soa(float* noalias nocapture %px,
                                   float* noalias nocapture %py,
                                   float* noalias nocapture readonly %pvx,
                                   float* noalias nocapture readonly %pvy,
                                   i32 %n) {
entry:
  %ext.n = zext i32 %n to i64
  br label %vector.body

vector.body:
  %index = phi i64 [ 0, %entry ], [ %index.next, %vector.body ]
  %gep.px = getelementptr inbounds float, float* %px, i64 %index
  %ptr.px = bitcast float* %gep.px to <8 x float>*
  %vx.px = load <8 x float>, <8 x float>* %ptr.px, align 4
  %gep.pvx = getelementptr inbounds float, float* %pvx, i64 %index
  %ptr.pvx = bitcast float* %gep.pvx to <8 x float>*
  %vx.pvx = load <8 x float>, <8 x float>* %ptr.pvx, align 4
  %px.new = fadd <8 x float> %vx.px, %vx.pvx
  store <8 x float> %px.new, <8 x float>* %ptr.px, align 4
  %gep.py = getelementptr inbounds float, float* %py, i64 %index
  %ptr.py = bitcast float* %gep.py to <8 x float>*
  %vx.py = load <8 x float>, <8 x float>* %ptr.py, align 4
  %gep.pvy = getelementptr inbounds float, float* %pvy, i64 %index
  %ptr.pvy = bitcast float* %gep.pvy to <8 x float>*
  %vx.pvy = load <8 x float>, <8 x float>* %ptr.pvy, align 4
  %py.new = fadd <8 x float> %vx.py, %vx.pvy
  store <8 x float> %py.new, <8 x float>* %ptr.py, align 4
  %index.next = add nuw i64 %index, 8
  %exitcond = icmp eq i64 %index.next, %ext.n
  br i1 %exitcond, label %exit, label %vector.body

exit:
  ret void
}
