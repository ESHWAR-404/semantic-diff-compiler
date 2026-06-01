; TC5 v2 — branchless / optimized control flow variants

define i32 @vec3_dominant_axis(i32 %x, i32 %y, i32 %z) {
entry:
  %ax.neg = icmp slt i32 %x, 0
  %ax = select i1 %ax.neg, i32 0, i32 %x
  %ay.neg = icmp slt i32 %y, 0
  %ay = select i1 %ay.neg, i32 0, i32 %y
  %az.neg = icmp slt i32 %z, 0
  %az = select i1 %az.neg, i32 0, i32 %z
  %cmp.xy = icmp sge i32 %ax, %ay
  %cmp.xz = icmp sge i32 %ax, %az
  %cmp.yz = icmp sge i32 %ay, %az
  %sel.xz = select i1 %cmp.xz, i32 0, i32 2
  %sel.yz = select i1 %cmp.yz, i32 1, i32 2
  %result = select i1 %cmp.xy, i32 %sel.xz, i32 %sel.yz
  ret i32 %result
}

define i32 @linear_search(i32* nocapture readonly %arr, i32 %n, i32 %target) {
entry:
  %cmp.empty = icmp sgt i32 %n, 0
  br i1 %cmp.empty, label %while.body.preheader, label %return.notfound

while.body.preheader:
  br label %while.body

while.body:
  %lo = phi i32 [ 0, %while.body.preheader ], [ %lo.next, %binary.less ], [ %lo, %binary.greater ]
  %hi = phi i32 [ %n.minus1, %while.body.preheader ], [ %hi, %binary.less ], [ %hi.next, %binary.greater ]
  %n.minus1 = sub i32 %n, 1
  %cmp.lohi = icmp sle i32 %lo, %hi
  br i1 %cmp.lohi, label %binary.body, label %return.notfound

binary.body:
  %sum = add i32 %lo, %hi
  %mid = lshr i32 %sum, 1
  %gep = getelementptr inbounds i32, i32* %arr, i32 %mid
  %val = load i32, i32* %gep, align 4
  %cmp.eq = icmp eq i32 %val, %target
  br i1 %cmp.eq, label %return.found, label %binary.check.lt

binary.check.lt:
  %cmp.lt = icmp slt i32 %val, %target
  br i1 %cmp.lt, label %binary.less, label %binary.greater

binary.less:
  %lo.next = add nsw i32 %mid, 1
  br label %while.body

binary.greater:
  %hi.next = sub nsw i32 %mid, 1
  br label %while.body

return.found:
  br label %return

return.notfound:
  br label %return

return:
  %retval = phi i32 [ %mid, %return.found ], [ -1, %return.notfound ]
  ret i32 %retval
}

define i32 @count_bits(i32 %x) {
entry:
  %cmp = icmp eq i32 %x, 0
  br i1 %cmp, label %while.end, label %while.body

while.body:
  %x.loop = phi i32 [ %x, %entry ], [ %x.cleared, %while.body ]
  %count = phi i32 [ 0, %entry ], [ %count.next, %while.body ]
  %x.minus1 = add i32 %x.loop, -1
  %x.cleared = and i32 %x.loop, %x.minus1
  %count.next = add nsw i32 %count, 1
  %cmp2 = icmp eq i32 %x.cleared, 0
  br i1 %cmp2, label %while.end, label %while.body

while.end:
  %count.0.lcssa = phi i32 [ 0, %entry ], [ %count.next, %while.body ]
  ret i32 %count.0.lcssa
}
