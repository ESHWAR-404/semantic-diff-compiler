; EVAL-09: After loop fusion — single vectorized pass over src

define void @process_arrays(float* noalias nocapture %a,
                             float* noalias nocapture %b,
                             float* noalias nocapture readonly %src, i32 %n) {
entry:
  %ext.n = zext i32 %n to i64
  br label %vector.body

vector.body:
  %index = phi i64 [ 0, %entry ], [ %index.next, %vector.body ]
  %gep.src = getelementptr inbounds float, float* %src, i64 %index
  %ptr.src = bitcast float* %gep.src to <8 x float>*
  %wide.src = load <8 x float>, <8 x float>* %ptr.src, align 4
  %val.a = fmul <8 x float> %wide.src, <float 2.0, float 2.0, float 2.0, float 2.0, float 2.0, float 2.0, float 2.0, float 2.0>
  %gep.a = getelementptr inbounds float, float* %a, i64 %index
  %ptr.a = bitcast float* %gep.a to <8 x float>*
  store <8 x float> %val.a, <8 x float>* %ptr.a, align 4
  %val.b = fmul <8 x float> %wide.src, <float 3.0, float 3.0, float 3.0, float 3.0, float 3.0, float 3.0, float 3.0, float 3.0>
  %gep.b = getelementptr inbounds float, float* %b, i64 %index
  %ptr.b = bitcast float* %gep.b to <8 x float>*
  store <8 x float> %val.b, <8 x float>* %ptr.b, align 4
  %index.next = add nuw i64 %index, 8
  %exitcond = icmp eq i64 %index.next, %ext.n
  br i1 %exitcond, label %for.end, label %vector.body

for.end:
  ret void
}
