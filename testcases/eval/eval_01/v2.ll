; EVAL-01: After — loop no longer unrolled (threshold tightened)

define i32 @compute_checksum(i8* nocapture readonly %data, i32 %len) {
entry:
  %cmp = icmp sgt i32 %len, 0
  br i1 %cmp, label %for.body.preheader, label %for.end

for.body.preheader:
  %wide.trip.count = zext i32 %len to i64
  br label %for.body

for.body:
  %iv = phi i64 [ 0, %for.body.preheader ], [ %iv.next, %for.body ]
  %sum = phi i32 [ 0, %for.body.preheader ], [ %sum.next, %for.body ]
  %gep = getelementptr inbounds i8, i8* %data, i64 %iv
  %v = load i8, i8* %gep, align 1
  %ext = zext i8 %v to i32
  %sum.next = add i32 %sum, %ext
  %iv.next = add nuw nsw i64 %iv, 1
  %exitcond = icmp eq i64 %iv.next, %wide.trip.count
  br i1 %exitcond, label %for.end.loopexit, label %for.body

for.end.loopexit:
  br label %for.end

for.end:
  %sum.lcssa = phi i32 [ 0, %entry ], [ %sum.next, %for.end.loopexit ]
  ret i32 %sum.lcssa
}
