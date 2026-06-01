; EVAL-07: Constant folding opportunity — before optimization

define i32 @get_page_size() {
entry:
  %page = mul i32 4, 1024
  ret i32 %page
}

define i32 @compute_buffer_size(i32 %count) {
entry:
  %page_size = call i32 @get_page_size()
  %header = add i32 %page_size, 64
  %total = mul i32 %header, %count
  ret i32 %total
}

define i32 @hash_combine(i32 %a, i32 %b) {
entry:
  %shift_left = shl i32 %a, 5
  %shift_right = lshr i32 %a, 27
  %rotated = or i32 %shift_left, %shift_right
  %mixed = xor i32 %rotated, %b
  %magic = mul i32 %mixed, 2654435761
  ret i32 %magic
}
