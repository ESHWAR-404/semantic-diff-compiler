; TC1 v1 — Fixed loop bounds: clang -O2 vectorizes and unrolls
; Target: x86_64 Linux

define void @sum_array(i32* nocapture readonly %arr, i32* nocapture %result) {
entry:
  br label %vector.body

vector.body:
  %index = phi i64 [ 0, %entry ], [ %index.next, %vector.body ]
  %vec.phi = phi <4 x i32> [ zeroinitializer, %entry ], [ %add.vec, %vector.body ]
  %gep = getelementptr inbounds i32, i32* %arr, i64 %index
  %ptr = bitcast i32* %gep to <4 x i32>*
  %wide.load = load <4 x i32>, <4 x i32>* %ptr, align 4
  %add.vec = add <4 x i32> %vec.phi, %wide.load
  %index.next = add nuw i64 %index, 4
  %done = icmp eq i64 %index.next, 16
  br i1 %done, label %middle.block, label %vector.body

middle.block:
  %rdx = call i32 @llvm.vector.reduce.add.v4i32(<4 x i32> %add.vec)
  br label %for.end

for.end:
  %sum.0.lcssa = phi i32 [ %rdx, %middle.block ]
  store i32 %sum.0.lcssa, i32* %result, align 4
  ret void
}

define void @scale_array(float* nocapture %arr, float %factor) {
entry:
  %factor.vec = insertelement <8 x float> undef, float %factor, i32 0
  %factor.splat = shufflevector <8 x float> %factor.vec, <8 x float> undef, <8 x i32> zeroinitializer
  br label %vector.body

vector.body:
  %index = phi i64 [ 0, %entry ], [ %index.next, %vector.body ]
  %gep = getelementptr inbounds float, float* %arr, i64 %index
  %ptr = bitcast float* %gep to <8 x float>*
  %wide.load = load <8 x float>, <8 x float>* %ptr, align 4
  %mul.vec = fmul <8 x float> %wide.load, %factor.splat
  %store.ptr = bitcast float* %gep to <8 x float>*
  store <8 x float> %mul.vec, <8 x float>* %store.ptr, align 4
  %index.next = add nuw i64 %index, 8
  %done = icmp eq i64 %index.next, 32
  br i1 %done, label %for.end, label %vector.body

for.end:
  ret void
}

declare i32 @llvm.vector.reduce.add.v4i32(<4 x i32>)
