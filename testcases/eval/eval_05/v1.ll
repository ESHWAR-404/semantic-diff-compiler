; EVAL-05: Tail call optimization NOT applied (recursive function)

define i64 @factorial(i64 %n) {
entry:
  %cmp = icmp ule i64 %n, 1
  br i1 %cmp, label %base.case, label %recursive.case

base.case:
  ret i64 1

recursive.case:
  %n.minus1 = sub i64 %n, 1
  %rec = call i64 @factorial(i64 %n.minus1)
  %result = mul i64 %n, %rec
  ret i64 %result
}

define i64 @fib(i64 %n) {
entry:
  %cmp1 = icmp ule i64 %n, 0
  br i1 %cmp1, label %base.0, label %check.1

check.1:
  %cmp2 = icmp eq i64 %n, 1
  br i1 %cmp2, label %base.1, label %recursive.fib

base.0:
  ret i64 0

base.1:
  ret i64 1

recursive.fib:
  %n1 = sub i64 %n, 1
  %n2 = sub i64 %n, 2
  %r1 = call i64 @fib(i64 %n1)
  %r2 = call i64 @fib(i64 %n2)
  %sum = add i64 %r1, %r2
  ret i64 %sum
}
