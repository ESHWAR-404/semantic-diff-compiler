; EVAL-01: Loop unrolling threshold change (inspired by LLVM commit rG5f3a2b1)
; Before: loop unrolled 4x (small trip count, constant bound)

define i32 @compute_checksum(i8* nocapture readonly %data, i32 %len) {
entry:
  %cmp = icmp sgt i32 %len, 0
  br i1 %cmp, label %for.body.preheader, label %for.end

for.body.preheader:
  %wide.trip.count = zext i32 %len to i64
  br label %for.body

for.body:
  %iv = phi i64 [ 0, %for.body.preheader ], [ %iv.next.3, %for.body ]
  %sum = phi i32 [ 0, %for.body.preheader ], [ %sum.3, %for.body ]

  %gep.0 = getelementptr inbounds i8, i8* %data, i64 %iv
  %v.0 = load i8, i8* %gep.0, align 1
  %ext.0 = zext i8 %v.0 to i32
  %sum.0 = add i32 %sum, %ext.0

  %iv.1 = add i64 %iv, 1
  %gep.1 = getelementptr inbounds i8, i8* %data, i64 %iv.1
  %v.1 = load i8, i8* %gep.1, align 1
  %ext.1 = zext i8 %v.1 to i32
  %sum.1 = add i32 %sum.0, %ext.1

  %iv.2 = add i64 %iv, 2
  %gep.2 = getelementptr inbounds i8, i8* %data, i64 %iv.2
  %v.2 = load i8, i8* %gep.2, align 1
  %ext.2 = zext i8 %v.2 to i32
  %sum.2 = add i32 %sum.1, %ext.2

  %iv.3 = add i64 %iv, 3
  %gep.3 = getelementptr inbounds i8, i8* %data, i64 %iv.3
  %v.3 = load i8, i8* %gep.3, align 1
  %ext.3 = zext i8 %v.3 to i32
  %sum.3 = add i32 %sum.2, %ext.3

  %iv.next.3 = add i64 %iv, 4
  %exitcond = icmp eq i64 %iv.next.3, %wide.trip.count
  br i1 %exitcond, label %for.end, label %for.body

for.end:
  %sum.lcssa = phi i32 [ 0, %entry ], [ %sum.3, %for.body ]
  ret i32 %sum.lcssa
}
