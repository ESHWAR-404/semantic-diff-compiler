; TC3 v1 — dead branches visible in IR

define i32 @classify_value(i32 %x) {
entry:
  %cmp.100 = icmp sgt i32 %x, 100
  br i1 %cmp.100, label %return.3, label %check.50

check.50:
  %cmp.50 = icmp sgt i32 %x, 50
  br i1 %cmp.50, label %return.2, label %check.0

check.0:
  %cmp.0 = icmp sgt i32 %x, 0
  br i1 %cmp.0, label %return.1, label %check.eq0

check.eq0:
  %cmp.eq = icmp eq i32 %x, 0
  br i1 %cmp.eq, label %return.0, label %return.neg

return.3:
  br label %return

return.2:
  br label %return

return.1:
  br label %return

return.0:
  br label %return

return.neg:
  br label %return

dead.code:
  br label %return

return:
  %retval = phi i32 [ 3, %return.3 ], [ 2, %return.2 ], [ 1, %return.1 ], [ 0, %return.0 ], [ -1, %return.neg ]
  ret i32 %retval
}

define i32 @safe_divide(i32 %a, i32 %b) {
entry:
  %cmp.zero = icmp eq i32 %b, 0
  br i1 %cmp.zero, label %return.zero, label %do.div

do.div:
  %div = sdiv i32 %a, %b
  %cmp.dead = icmp eq i32 %b, 0
  br i1 %cmp.dead, label %dead.branch, label %cont

dead.branch:
  br label %cont

cont:
  %result = phi i32 [ %div, %do.div ], [ -1, %dead.branch ]
  br label %return

return.zero:
  br label %return

return:
  %retval = phi i32 [ %result, %cont ], [ 0, %return.zero ]
  ret i32 %retval
}

define i32 @dispatch(i32 %op, i32 %a, i32 %b) {
entry:
  %cmp.add = icmp eq i32 %op, 0
  br i1 %cmp.add, label %op.add, label %check.sub

check.sub:
  %cmp.sub = icmp eq i32 %op, 1
  br i1 %cmp.sub, label %op.sub, label %check.mul

check.mul:
  %cmp.mul = icmp eq i32 %op, 2
  br i1 %cmp.mul, label %op.mul, label %check.div

check.div:
  %cmp.div = icmp eq i32 %op, 3
  br i1 %cmp.div, label %op.div.check, label %check.unk

check.unk:
  %cmp.unk = icmp eq i32 %op, 4
  br i1 %cmp.unk, label %op.unk, label %op.default

op.add:
  %radd = add nsw i32 %a, %b
  br label %return

op.sub:
  %rsub = sub nsw i32 %a, %b
  br label %return

op.mul:
  %rmul = mul nsw i32 %a, %b
  br label %return

op.div.check:
  %iszero = icmp eq i32 %b, 0
  br i1 %iszero, label %op.div.zero, label %op.div.ok

op.div.ok:
  %rdiv = sdiv i32 %a, %b
  br label %return

op.div.zero:
  br label %return

op.unk:
  br label %return

op.default:
  br label %return

return:
  %retval = phi i32 [ %radd, %op.add ], [ %rsub, %op.sub ], [ %rmul, %op.mul ],
                    [ %rdiv, %op.div.ok ], [ 0, %op.div.zero ],
                    [ 0, %op.unk ], [ 0, %op.default ]
  ret i32 %retval
}
