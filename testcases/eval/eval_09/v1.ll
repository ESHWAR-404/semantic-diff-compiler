; EVAL-09: Loop fusion — two loops merged into one

define void @process_arrays(float* nocapture %a, float* nocapture %b,
                             float* nocapture readonly %src, i32 %n) {
entry:
  %ext.n = zext i32 %n to i64
  br label %loop1.body

loop1.body:
  %iv1 = phi i64 [ 0, %entry ], [ %iv1.next, %loop1.body ]
  %gep.src = getelementptr inbounds float, float* %src, i64 %iv1
  %val.src = load float, float* %gep.src, align 4
  %gep.a = getelementptr inbounds float, float* %a, i64 %iv1
  %val.a = fmul float %val.src, 2.0
  store float %val.a, float* %gep.a, align 4
  %iv1.next = add nuw nsw i64 %iv1, 1
  %exitcond1 = icmp eq i64 %iv1.next, %ext.n
  br i1 %exitcond1, label %loop2.preheader, label %loop1.body

loop2.preheader:
  br label %loop2.body

loop2.body:
  %iv2 = phi i64 [ 0, %loop2.preheader ], [ %iv2.next, %loop2.body ]
  %gep.src2 = getelementptr inbounds float, float* %src, i64 %iv2
  %val.src2 = load float, float* %gep.src2, align 4
  %gep.b = getelementptr inbounds float, float* %b, i64 %iv2
  %val.b = fmul float %val.src2, 3.0
  store float %val.b, float* %gep.b, align 4
  %iv2.next = add nuw nsw i64 %iv2, 1
  %exitcond2 = icmp eq i64 %iv2.next, %ext.n
  br i1 %exitcond2, label %for.end, label %loop2.body

for.end:
  ret void
}
