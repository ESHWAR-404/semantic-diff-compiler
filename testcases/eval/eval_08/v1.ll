; EVAL-08: Vectorization gained via loop restructuring (AoS → SoA)
; Before: Array-of-Structs layout — stride prevents auto-vectorization

define void @update_particles_aos(float* nocapture %particles, i32 %n, float %dt) {
entry:
  %cmp = icmp sgt i32 %n, 0
  br i1 %cmp, label %for.body.preheader, label %for.end

for.body.preheader:
  %ext.n = zext i32 %n to i64
  br label %for.body

for.body:
  %iv = phi i64 [ 0, %for.body.preheader ], [ %iv.next, %for.body ]
  ; Each particle: struct { float x, y, z, vx, vy, vz; } → stride = 6 floats
  %base = mul i64 %iv, 6
  %gep.x  = getelementptr inbounds float, float* %particles, i64 %base
  %x = load float, float* %gep.x, align 4
  %base.vx = add i64 %base, 3
  %gep.vx = getelementptr inbounds float, float* %particles, i64 %base.vx
  %vx = load float, float* %gep.vx, align 4
  %x.new = fadd float %x, %vx
  store float %x.new, float* %gep.x, align 4
  %base.y = add i64 %base, 1
  %gep.y = getelementptr inbounds float, float* %particles, i64 %base.y
  %y = load float, float* %gep.y, align 4
  %base.vy = add i64 %base, 4
  %gep.vy = getelementptr inbounds float, float* %particles, i64 %base.vy
  %vy = load float, float* %gep.vy, align 4
  %y.new = fadd float %y, %vy
  store float %y.new, float* %gep.y, align 4
  %iv.next = add nuw nsw i64 %iv, 1
  %exitcond = icmp eq i64 %iv.next, %ext.n
  br i1 %exitcond, label %for.end.loopexit, label %for.body

for.end.loopexit:
  br label %for.end

for.end:
  ret void
}
