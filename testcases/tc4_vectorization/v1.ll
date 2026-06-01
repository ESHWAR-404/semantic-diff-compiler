; TC4 v1 — scalar loops (aliasing prevents vectorization)

define void @multiply_arrays(float* %out, float* %a, float* %b, i32 %n) {
entry:
  %cmp3 = icmp sgt i32 %n, 0
  br i1 %cmp3, label %for.body.preheader, label %for.end

for.body.preheader:
  %wide.trip.count = zext i32 %n to i64
  br label %for.body

for.body:
  %iv = phi i64 [ 0, %for.body.preheader ], [ %iv.next, %for.body ]
  %gep.a = getelementptr inbounds float, float* %a, i64 %iv
  %va = load float, float* %gep.a, align 4
  %gep.b = getelementptr inbounds float, float* %b, i64 %iv
  %vb = load float, float* %gep.b, align 4
  %mul = fmul float %va, %vb
  %gep.out = getelementptr inbounds float, float* %out, i64 %iv
  store float %mul, float* %gep.out, align 4
  %iv.next = add nuw nsw i64 %iv, 1
  %exitcond = icmp eq i64 %iv.next, %wide.trip.count
  br i1 %exitcond, label %for.end.loopexit, label %for.body

for.end.loopexit:
  br label %for.end

for.end:
  ret void
}

define void @saxpy(float* %y, float %alpha, float* %x, i32 %n) {
entry:
  %cmp3 = icmp sgt i32 %n, 0
  br i1 %cmp3, label %for.body.preheader, label %for.end

for.body.preheader:
  %wide.trip.count = zext i32 %n to i64
  br label %for.body

for.body:
  %iv = phi i64 [ 0, %for.body.preheader ], [ %iv.next, %for.body ]
  %gep.x = getelementptr inbounds float, float* %x, i64 %iv
  %vx = load float, float* %gep.x, align 4
  %gep.y = getelementptr inbounds float, float* %y, i64 %iv
  %vy = load float, float* %gep.y, align 4
  %mul = fmul float %alpha, %vx
  %add = fadd float %mul, %vy
  store float %add, float* %gep.y, align 4
  %iv.next = add nuw nsw i64 %iv, 1
  %exitcond = icmp eq i64 %iv.next, %wide.trip.count
  br i1 %exitcond, label %for.end.loopexit, label %for.body

for.end.loopexit:
  br label %for.end

for.end:
  ret void
}
