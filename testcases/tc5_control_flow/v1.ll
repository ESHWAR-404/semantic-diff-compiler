; TC5 v1 — nested conditionals and simple while loops

define i32 @vec3_dominant_axis(i32 %x, i32 %y, i32 %z) {
entry:
  %ax.neg = icmp slt i32 %x, 0
  %ax.abs = select i1 %ax.neg, i32 0, i32 %x
  %ax = sub i32 %ax.abs, (select i1 %ax.neg, i32 %x, i32 0)
  %ay.neg = icmp slt i32 %y, 0
  %ay.abs = select i1 %ay.neg, i32 0, i32 %y
  %ay = sub i32 %ay.abs, (select i1 %ay.neg, i32 %y, i32 0)
  %az.neg = icmp slt i32 %z, 0
  %az.abs = select i1 %az.neg, i32 0, i32 %z
  %az = sub i32 %az.abs, (select i1 %az.neg, i32 %z, i32 0)
  %cmp.xy = icmp sge i32 %ax, %ay
  br i1 %cmp.xy, label %if.ax.ge.ay, label %else.ay.gt.ax

if.ax.ge.ay:
  %cmp.xz = icmp sge i32 %ax, %az
  br i1 %cmp.xz, label %return.0, label %return.2.a

else.ay.gt.ax:
  %cmp.yz = icmp sge i32 %ay, %az
  br i1 %cmp.yz, label %return.1, label %return.2.b

return.0:
  br label %return

return.1:
  br label %return

return.2.a:
  br label %return

return.2.b:
  br label %return

return:
  %retval = phi i32 [ 0, %return.0 ], [ 1, %return.1 ],
                    [ 2, %return.2.a ], [ 2, %return.2.b ]
  ret i32 %retval
}

define i32 @linear_search(i32* nocapture readonly %arr, i32 %n, i32 %target) {
entry:
  %cmp3 = icmp sgt i32 %n, 0
  br i1 %cmp3, label %for.body.preheader, label %return.notfound

for.body.preheader:
  br label %for.body

for.body:
  %i = phi i32 [ 0, %for.body.preheader ], [ %i.next, %continue ]
  %gep = getelementptr inbounds i32, i32* %arr, i32 %i
  %val = load i32, i32* %gep, align 4
  %cmp.eq = icmp eq i32 %val, %target
  br i1 %cmp.eq, label %return.found, label %check.gt

check.gt:
  %cmp.gt = icmp sgt i32 %val, %target
  br i1 %cmp.gt, label %return.notfound.early, label %continue

continue:
  %i.next = add nuw nsw i32 %i, 1
  %exitcond = icmp eq i32 %i.next, %n
  br i1 %exitcond, label %return.notfound, label %for.body

return.found:
  br label %return

return.notfound.early:
  br label %return

return.notfound:
  br label %return

return:
  %retval = phi i32 [ %i, %return.found ], [ -1, %return.notfound.early ], [ -1, %return.notfound ]
  ret i32 %retval
}

define i32 @count_bits(i32 %x) {
entry:
  %cmp = icmp eq i32 %x, 0
  br i1 %cmp, label %while.end, label %while.body

while.body:
  %x.loop = phi i32 [ %x, %entry ], [ %x.shr, %while.body ]
  %count = phi i32 [ 0, %entry ], [ %count.next, %while.body ]
  %bit = and i32 %x.loop, 1
  %count.next = add nsw i32 %count, %bit
  %x.shr = lshr i32 %x.loop, 1
  %cmp2 = icmp eq i32 %x.shr, 0
  br i1 %cmp2, label %while.end, label %while.body

while.end:
  %count.0.lcssa = phi i32 [ 0, %entry ], [ %count.next, %while.body ]
  ret i32 %count.0.lcssa
}
