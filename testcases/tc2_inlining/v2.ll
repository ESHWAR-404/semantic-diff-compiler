; TC2 v2 — always_inline: helpers merged into callers, no separate call sites

; clamp and dot_product_elem are gone — fully inlined, removed from module

define void @clamp_array(i32* nocapture %arr, i32 %n, i32 %lo, i32 %hi) {
entry:
  %cmp4 = icmp sgt i32 %n, 0
  br i1 %cmp4, label %for.body.preheader, label %for.end

for.body.preheader:
  %wide.trip.count = zext i32 %n to i64
  br label %for.body

for.body:
  %indvars.iv = phi i64 [ 0, %for.body.preheader ], [ %indvars.iv.next, %for.body ]
  %arrayidx = getelementptr inbounds i32, i32* %arr, i64 %indvars.iv
  %val = load i32, i32* %arrayidx, align 4
  %cmp.lo = icmp slt i32 %val, %lo
  %sel.lo = select i1 %cmp.lo, i32 %lo, i32 %val
  %cmp.hi = icmp sgt i32 %sel.lo, %hi
  %clamped = select i1 %cmp.hi, i32 %hi, i32 %sel.lo
  store i32 %clamped, i32* %arrayidx, align 4
  %indvars.iv.next = add nuw nsw i64 %indvars.iv, 1
  %exitcond.not = icmp eq i64 %indvars.iv.next, %wide.trip.count
  br i1 %exitcond.not, label %for.end.loopexit, label %for.body

for.end.loopexit:
  br label %for.end

for.end:
  ret void
}

define i32 @dot_product(i32* nocapture readonly %a, i32* nocapture readonly %b, i32 %n) {
entry:
  %cmp3 = icmp sgt i32 %n, 0
  br i1 %cmp3, label %for.body.preheader, label %for.end

for.body.preheader:
  br label %for.body

for.body:
  %i.04 = phi i32 [ 0, %for.body.preheader ], [ %inc, %for.body ]
  %result.03 = phi i32 [ 0, %for.body.preheader ], [ %add, %for.body ]
  %idxprom = sext i32 %i.04 to i64
  %arrayidx.a = getelementptr inbounds i32, i32* %a, i64 %idxprom
  %va = load i32, i32* %arrayidx.a, align 4
  %arrayidx.b = getelementptr inbounds i32, i32* %b, i64 %idxprom
  %vb = load i32, i32* %arrayidx.b, align 4
  %mul = mul nsw i32 %va, %vb
  %add = add nsw i32 %result.03, %mul
  %inc = add nuw nsw i32 %i.04, 1
  %exitcond.not = icmp eq i32 %inc, %n
  br i1 %exitcond.not, label %for.end.loopexit, label %for.body

for.end.loopexit:
  br label %for.end

for.end:
  %result.0.lcssa = phi i32 [ 0, %entry ], [ %add, %for.end.loopexit ]
  ret i32 %result.0.lcssa
}
