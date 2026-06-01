; TC4 v2 — vectorized loops via __restrict__ (no aliasing)

define void @multiply_arrays(float* noalias nocapture %out,
                              float* noalias nocapture readonly %a,
                              float* noalias nocapture readonly %b, i32 %n) {
entry:
  %cmp3 = icmp sgt i32 %n, 0
  br i1 %cmp3, label %for.body.preheader, label %for.end

for.body.preheader:
  %wide.trip.count = zext i32 %n to i64
  br label %vector.body

vector.body:
  %index = phi i64 [ 0, %for.body.preheader ], [ %index.next, %vector.body ]
  %gep.a = getelementptr inbounds float, float* %a, i64 %index
  %ptr.a = bitcast float* %gep.a to <8 x float>*
  %wide.load.a = load <8 x float>, <8 x float>* %ptr.a, align 4
  %gep.b = getelementptr inbounds float, float* %b, i64 %index
  %ptr.b = bitcast float* %gep.b to <8 x float>*
  %wide.load.b = load <8 x float>, <8 x float>* %ptr.b, align 4
  %mul.vec = fmul <8 x float> %wide.load.a, %wide.load.b
  %gep.out = getelementptr inbounds float, float* %out, i64 %index
  %ptr.out = bitcast float* %gep.out to <8 x float>*
  store <8 x float> %mul.vec, <8 x float>* %ptr.out, align 4
  %index.next = add nuw i64 %index, 8
  %exitcond = icmp eq i64 %index.next, %wide.trip.count
  br i1 %exitcond, label %for.end, label %vector.body

for.end:
  ret void
}

define void @saxpy(float* noalias nocapture %y, float %alpha,
                   float* noalias nocapture readonly %x, i32 %n) {
entry:
  %cmp3 = icmp sgt i32 %n, 0
  br i1 %cmp3, label %for.body.preheader, label %for.end

for.body.preheader:
  %wide.trip.count = zext i32 %n to i64
  %alpha.vec0 = insertelement <8 x float> undef, float %alpha, i32 0
  %alpha.splat = shufflevector <8 x float> %alpha.vec0, <8 x float> undef, <8 x i32> zeroinitializer
  br label %vector.body

vector.body:
  %index = phi i64 [ 0, %for.body.preheader ], [ %index.next, %vector.body ]
  %gep.x = getelementptr inbounds float, float* %x, i64 %index
  %ptr.x = bitcast float* %gep.x to <8 x float>*
  %wide.load.x = load <8 x float>, <8 x float>* %ptr.x, align 4
  %gep.y = getelementptr inbounds float, float* %y, i64 %index
  %ptr.y = bitcast float* %gep.y to <8 x float>*
  %wide.load.y = load <8 x float>, <8 x float>* %ptr.y, align 4
  %mul.vec = fmul <8 x float> %alpha.splat, %wide.load.x
  %add.vec = fadd <8 x float> %mul.vec, %wide.load.y
  store <8 x float> %add.vec, <8 x float>* %ptr.y, align 4
  %index.next = add nuw i64 %index, 8
  %exitcond = icmp eq i64 %index.next, %wide.trip.count
  br i1 %exitcond, label %for.end, label %vector.body

for.end:
  ret void
}
