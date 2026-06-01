; EVAL-02: Vectorization width change — AVX2 (256-bit) to SSE4.2 (128-bit) target
; Before: 8-wide float vectorization (AVX2)

define void @matrix_multiply_row(float* noalias nocapture %c,
                                  float* noalias nocapture readonly %a,
                                  float* noalias nocapture readonly %b, i32 %n) {
entry:
  %wide.trip.count = zext i32 %n to i64
  %a0.vec = insertelement <8 x float> undef, float 0.0, i32 0
  br label %vector.body

vector.body:
  %index = phi i64 [ 0, %entry ], [ %index.next, %vector.body ]
  %acc = phi <8 x float> [ %a0.vec, %entry ], [ %acc.next, %vector.body ]
  %gep.b = getelementptr inbounds float, float* %b, i64 %index
  %ptr.b = bitcast float* %gep.b to <8 x float>*
  %wide.b = load <8 x float>, <8 x float>* %ptr.b, align 32
  %gep.a = getelementptr inbounds float, float* %a, i64 %index
  %ptr.a = bitcast float* %gep.a to <8 x float>*
  %wide.a = load <8 x float>, <8 x float>* %ptr.a, align 32
  %prod = fmul <8 x float> %wide.a, %wide.b
  %acc.next = fadd <8 x float> %acc, %prod
  %index.next = add nuw i64 %index, 8
  %exitcond = icmp eq i64 %index.next, %wide.trip.count
  br i1 %exitcond, label %exit, label %vector.body

exit:
  %reduce = call float @llvm.vector.reduce.fadd.v8f32(float 0.0, <8 x float> %acc.next)
  %gep.c0 = getelementptr inbounds float, float* %c, i64 0
  store float %reduce, float* %gep.c0, align 4
  ret void
}

declare float @llvm.vector.reduce.fadd.v8f32(float, <8 x float>)
