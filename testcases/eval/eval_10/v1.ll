; EVAL-10: Signature change (int → long) affects vectorization width

define void @prefix_sum_i32(i32* nocapture %arr, i32 %n) {
entry:
  %cmp = icmp sgt i32 %n, 0
  br i1 %cmp, label %for.body.preheader, label %for.end

for.body.preheader:
  %ext.n = zext i32 %n to i64
  br label %for.body

for.body:
  %iv = phi i64 [ 1, %for.body.preheader ], [ %iv.next, %for.body ]
  %prev.idx = sub i64 %iv, 1
  %gep.prev = getelementptr inbounds i32, i32* %arr, i64 %prev.idx
  %prev.val = load i32, i32* %gep.prev, align 4
  %gep.cur = getelementptr inbounds i32, i32* %arr, i64 %iv
  %cur.val = load i32, i32* %gep.cur, align 4
  %new.val = add i32 %prev.val, %cur.val
  store i32 %new.val, i32* %gep.cur, align 4
  %iv.next = add nuw nsw i64 %iv, 1
  %exitcond = icmp eq i64 %iv.next, %ext.n
  br i1 %exitcond, label %for.end.loopexit, label %for.body

for.end.loopexit:
  br label %for.end

for.end:
  ret void
}

define i32 @reduce_max_i32(i32* nocapture readonly %arr, i32 %n) {
entry:
  %cmp = icmp sgt i32 %n, 0
  br i1 %cmp, label %for.body.preheader, label %for.end

for.body.preheader:
  %ext.n = zext i32 %n to i64
  br label %for.body

for.body:
  %iv = phi i64 [ 0, %for.body.preheader ], [ %iv.next, %for.body ]
  %max.prev = phi i32 [ -2147483648, %for.body.preheader ], [ %max.next, %for.body ]
  %gep = getelementptr inbounds i32, i32* %arr, i64 %iv
  %val = load i32, i32* %gep, align 4
  %cmp.gt = icmp sgt i32 %val, %max.prev
  %max.next = select i1 %cmp.gt, i32 %val, i32 %max.prev
  %iv.next = add nuw nsw i64 %iv, 1
  %exitcond = icmp eq i64 %iv.next, %ext.n
  br i1 %exitcond, label %for.end.loopexit, label %for.body

for.end.loopexit:
  br label %for.end

for.end:
  %max.lcssa = phi i32 [ -2147483648, %entry ], [ %max.next, %for.end.loopexit ]
  ret i32 %max.lcssa
}
