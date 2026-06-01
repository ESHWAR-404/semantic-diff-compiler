; EVAL-03: After — fast_abs inlined into normalize_signal, function removed

; fast_abs is gone from module

define void @normalize_signal(i32* nocapture %buf, i32 %n, i32 %scale) {
entry:
  %cmp = icmp sgt i32 %n, 0
  br i1 %cmp, label %for.body.preheader, label %for.end

for.body.preheader:
  %ext.n = zext i32 %n to i64
  br label %for.body

for.body:
  %iv = phi i64 [ 0, %for.body.preheader ], [ %iv.next, %for.body ]
  %gep = getelementptr inbounds i32, i32* %buf, i64 %iv
  %val = load i32, i32* %gep, align 4
  %neg = sub nsw i32 0, %val
  %cmp.lt = icmp slt i32 %val, 0
  %absval = select i1 %cmp.lt, i32 %neg, i32 %val
  %scaled = sdiv i32 %absval, %scale
  store i32 %scaled, i32* %gep, align 4
  %iv.next = add nuw nsw i64 %iv, 1
  %exitcond = icmp eq i64 %iv.next, %ext.n
  br i1 %exitcond, label %for.end.loopexit, label %for.body

for.end.loopexit:
  br label %for.end

for.end:
  ret void
}
