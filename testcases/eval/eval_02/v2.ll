; EVAL-02: After — 4-wide float vectorization (SSE4.2 target, no AVX2)

define void @matrix_multiply_row(float* noalias nocapture %c,
                                  float* noalias nocapture readonly %a,
                                  float* noalias nocapture readonly %b, i32 %n) {
entry:
  %wide.trip.count = zext i32 %n to i64
  %a0.vec = insertelement <4 x float> undef, float 0.0, i32 0
  br label %vector.body

vector.body:
  %index = phi i64 [ 0, %entry ], [ %index.next, %vector.body ]
  %acc = phi <4 x float> [ %a0.vec, %entry ], [ %acc.next, %vector.body ]
  %gep.b = getelementptr inbounds float, float* %b, i64 %index
  %ptr.b = bitcast float* %gep.b to <4 x float>*
  %wide.b = load <4 x float>, <4 x float>* %ptr.b, align 16
  %gep.a = getelementptr inbounds float, float* %a, i64 %index
  %ptr.a = bitcast float* %gep.a to <4 x float>*
  %wide.a = load <4 x float>, <4 x float>* %ptr.a, align 16
  %prod = fmul <4 x float> %wide.a, %wide.b
  %acc.next = fadd <4 x float> %acc, %prod
  %index.next = add nuw i64 %index, 4
  %exitcond = icmp eq i64 %index.next, %wide.trip.count
  br i1 %exitcond, label %exit, label %vector.body

exit:
  %reduce = call float @llvm.vector.reduce.fadd.v4f32(float 0.0, <4 x float> %acc.next)
  %gep.c0 = getelementptr inbounds float, float* %c, i64 0
  store float %reduce, float* %gep.c0, align 4
  ret void
}

declare float @llvm.vector.reduce.fadd.v4f32(float, <4 x float>)
