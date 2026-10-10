     records = [
         {"id": "T001", "owner": "Chen", "status": "closed", "created_at": "2026-10-12T09:00:00+08:00", "closed_at": "2026-10-12T11:30:00+08:00"},
         {"id": "T001", "owner": "Chen", "status": "closed", "created_at": "2026-10-12T09:00:00+08:00", "closed_at": "2026-10-12T11:30:00+08:00"}
     ]
     

# ----- 下一个片段 -----

     records = [
         {"status": "CLOSED"},
         {"status": "  open  "},
         {"status": "processing"},
         {"status": "unknown"}
     ]
     

# ----- 下一个片段 -----

     records = [
         {"owner": None},
         {"owner": "  "},
         {"owner": "Chen"}
     ]
     

# ----- 下一个片段 -----

     records = [
         {"closed_at": "invalid_date"},
         {"closed_at": "2026-10-12T11:30:00+08:00"}
     ]
     

# ----- 下一个片段 -----

     records = [
         {"created_at": "2026-10-12T09:00:00+08:00", "closed_at": "2026-10-12T11:30:00+09:00"},
         {"created_at": "2026-10-12T14:00:00", "closed_at": "2026-10-12T18:15:00"}
     ]
     

# ----- 下一个片段 -----

     records = [
         {"created_at": "2026-10-12T11:30:00+08:00", "closed_at": "2026-10-12T09:00:00+08:00"}
     ]
     