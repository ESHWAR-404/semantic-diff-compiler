; TC3 v2 — dead branches eliminated; switch replaces if-chain for dispatch

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
  br label %return

return.zero:
  br label %return

return:
  %retval = phi i32 [ %div, %do.div ], [ 0, %return.zero ]
  ret i32 %retval
}

define i32 @dispatch(i32 %op, i32 %a, i32 %b) {
entry:
  switch i32 %op, label %sw.default [
    i32 0, label %sw.add
    i32 1, label %sw.sub
    i32 2, label %sw.mul
    i32 3, label %sw.div.check
  ]

sw.add:
  %radd = add nsw i32 %a, %b
  br label %return

sw.sub:
  %rsub = sub nsw i32 %a, %b
  br label %return

sw.mul:
  %rmul = mul nsw i32 %a, %b
  br label %return

sw.div.check:
  %iszero = icmp eq i32 %b, 0
  br i1 %iszero, label %sw.div.zero, label %sw.div.ok

sw.div.ok:
  %rdiv = sdiv i32 %a, %b
  br label %return

sw.div.zero:
  br label %return

sw.default:
  br label %return

return:
  %retval = phi i32 [ %radd, %sw.add ], [ %rsub, %sw.sub ], [ %rmul, %sw.mul ],
                    [ %rdiv, %sw.div.ok ], [ 0, %sw.div.zero ], [ 0, %sw.default ]
  ret i32 %retval
}
