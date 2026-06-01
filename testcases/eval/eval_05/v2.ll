; EVAL-05: Tail-recursive factorial (accumulator style) — TCO applicable
; fib converted to iterative

define i64 @factorial(i64 %n) {
entry:
  br label %tail.loop

tail.loop:
  %n.cur = phi i64 [ %n, %entry ], [ %n.next, %continue ]
  %acc = phi i64 [ 1, %entry ], [ %acc.next, %continue ]
  %cmp = icmp ule i64 %n.cur, 1
  br i1 %cmp, label %done, label %continue

continue:
  %acc.next = mul i64 %acc, %n.cur
  %n.next = sub i64 %n.cur, 1
  br label %tail.loop

done:
  ret i64 %acc
}

define i64 @fib(i64 %n) {
entry:
  %cmp1 = icmp ule i64 %n, 1
  br i1 %cmp1, label %base.case, label %for.body.preheader

base.case:
  ret i64 %n

for.body.preheader:
  br label %for.body

for.body:
  %i = phi i64 [ 2, %for.body.preheader ], [ %i.next, %for.body ]
  %a = phi i64 [ 0, %for.body.preheader ], [ %b, %for.body ]
  %b = phi i64 [ 1, %for.body.preheader ], [ %c, %for.body ]
  %c = add i64 %a, %b
  %i.next = add nuw i64 %i, 1
  %exitcond = icmp eq i64 %i.next, %n
  br i1 %exitcond, label %for.end, label %for.body

for.end:
  ret i64 %c
}
