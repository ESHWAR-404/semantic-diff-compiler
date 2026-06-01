; EVAL-04: After dead store elimination pass

define void @init_buffer(i32* nocapture %buf, i32 %n, i32 %val) {
entry:
  %cmp = icmp sgt i32 %n, 0
  br i1 %cmp, label %for.body.preheader, label %for.end

for.body.preheader:
  %ext.n = zext i32 %n to i64
  %computed = add i32 %val, 1
  br label %for.body

for.body:
  %iv = phi i64 [ 0, %for.body.preheader ], [ %iv.next, %for.body ]
  %gep = getelementptr inbounds i32, i32* %buf, i64 %iv
  store i32 %computed, i32* %gep, align 4
  %iv.next = add nuw nsw i64 %iv, 1
  %exitcond = icmp eq i64 %iv.next, %ext.n
  br i1 %exitcond, label %for.end.loopexit, label %for.body

for.end.loopexit:
  br label %for.end

for.end:
  ret void
}

define i32 @compute_with_temp(i32 %a, i32 %b) {
entry:
  %sum = add i32 %a, %b
  %result = add i32 %sum, 1
  ret i32 %result
}
