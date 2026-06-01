; EVAL-07: After constant folding and inlining

define i32 @get_page_size() {
entry:
  ret i32 4096
}

define i32 @compute_buffer_size(i32 %count) {
entry:
  %total = mul i32 %count, 4160
  ret i32 %total
}

define i32 @hash_combine(i32 %a, i32 %b) {
entry:
  %shift_left = shl i32 %a, 5
  %shift_right = lshr i32 %a, 27
  %rotated = or i32 %shift_left, %shift_right
  %mixed = xor i32 %rotated, %b
  %magic = mul i32 %mixed, -1640531527
  ret i32 %magic
}
