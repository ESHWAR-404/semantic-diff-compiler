; EVAL-10: After — i32 → i64 type upgrade (64-bit indices/values)
; Changes return type and accumulator type

define void @prefix_sum_i32(i64* nocapture %arr, i64 %n) {
entry:
  %cmp = icmp sgt i64 %n, 0
  br i1 %cmp, label %for.body.preheader, label %for.end

for.body.preheader:
  br label %for.body

for.body:
  %iv = phi i64 [ 1, %for.body.preheader ], [ %iv.next, %for.body ]
  %prev.idx = sub i64 %iv, 1
  %gep.prev = getelementptr inbounds i64, i64* %arr, i64 %prev.idx
  %prev.val = load i64, i64* %gep.prev, align 8
  %gep.cur = getelementptr inbounds i64, i64* %arr, i64 %iv
  %cur.val = load i64, i64* %gep.cur, align 8
  %new.val = add i64 %prev.val, %cur.val
  store i64 %new.val, i64* %gep.cur, align 8
  %iv.next = add nuw nsw i64 %iv, 1
  %exitcond = icmp eq i64 %iv.next, %n
  br i1 %exitcond, label %for.end.loopexit, label %for.body

for.end.loopexit:
  br label %for.end

for.end:
  ret void
}

define i64 @reduce_max_i32(i64* nocapture readonly %arr, i64 %n) {
entry:
  %cmp = icmp sgt i64 %n, 0
  br i1 %cmp, label %for.body.preheader, label %for.end

for.body.preheader:
  br label %for.body

for.body:
  %iv = phi i64 [ 0, %for.body.preheader ], [ %iv.next, %for.body ]
  %max.prev = phi i64 [ -9223372036854775808, %for.body.preheader ], [ %max.next, %for.body ]
  %gep = getelementptr inbounds i64, i64* %arr, i64 %iv
  %val = load i64, i64* %gep, align 8
  %cmp.gt = icmp sgt i64 %val, %max.prev
  %max.next = select i1 %cmp.gt, i64 %val, i64 %max.prev
  %iv.next = add nuw nsw i64 %iv, 1
  %exitcond = icmp eq i64 %iv.next, %n
  br i1 %exitcond, label %for.end.loopexit, label %for.body

for.end.loopexit:
  br label %for.end

for.end:
  %max.lcssa = phi i64 [ -9223372036854775808, %entry ], [ %max.next, %for.end.loopexit ]
  ret i64 %max.lcssa
}
