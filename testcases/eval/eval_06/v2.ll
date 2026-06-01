; EVAL-06: After — vectorized version added as new function

define float @l2_norm_scalar(float* nocapture readonly %v, i32 %n) {
entry:
  %cmp = icmp sgt i32 %n, 0
  br i1 %cmp, label %for.body.preheader, label %for.end

for.body.preheader:
  %ext.n = zext i32 %n to i64
  br label %for.body

for.body:
  %iv = phi i64 [ 0, %for.body.preheader ], [ %iv.next, %for.body ]
  %acc = phi float [ 0.0, %for.body.preheader ], [ %acc.next, %for.body ]
  %gep = getelementptr inbounds float, float* %v, i64 %iv
  %val = load float, float* %gep, align 4
  %sq = fmul float %val, %val
  %acc.next = fadd float %acc, %sq
  %iv.next = add nuw nsw i64 %iv, 1
  %exitcond = icmp eq i64 %iv.next, %ext.n
  br i1 %exitcond, label %for.end.loopexit, label %for.body

for.end.loopexit:
  br label %for.end

for.end:
  %acc.lcssa = phi float [ 0.0, %entry ], [ %acc.next, %for.end.loopexit ]
  %result = call float @llvm.sqrt.f32(float %acc.lcssa)
  ret float %result
}

define float @l2_norm_avx(float* noalias nocapture readonly %v, i32 %n) {
entry:
  %ext.n = zext i32 %n to i64
  br label %vector.body

vector.body:
  %index = phi i64 [ 0, %entry ], [ %index.next, %vector.body ]
  %acc.vec = phi <8 x float> [ zeroinitializer, %entry ], [ %acc.vec.next, %vector.body ]
  %gep = getelementptr inbounds float, float* %v, i64 %index
  %ptr = bitcast float* %gep to <8 x float>*
  %wide = load <8 x float>, <8 x float>* %ptr, align 32
  %sq.vec = fmul <8 x float> %wide, %wide
  %acc.vec.next = fadd <8 x float> %acc.vec, %sq.vec
  %index.next = add nuw i64 %index, 8
  %exitcond = icmp eq i64 %index.next, %ext.n
  br i1 %exitcond, label %exit, label %vector.body

exit:
  %sum = call float @llvm.vector.reduce.fadd.v8f32(float 0.0, <8 x float> %acc.vec.next)
  %result = call float @llvm.sqrt.f32(float %sum)
  ret float %result
}

declare float @llvm.sqrt.f32(float)
declare float @llvm.vector.reduce.fadd.v8f32(float, <8 x float>)
