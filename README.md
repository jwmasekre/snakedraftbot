# snakedraftbot

discord bot for running snake drafts

## commands

### $sample

sends a sample csv

### $test

test

### $initiate [opt-in]

starts a draft; if opt-in is not included, all non-bots are auto-added to the member list

### $opt_in draft_id

opt in to a draft

### $opt_out draft_id

opt out of a draft

### $cancel draft_id

cancels a draft

### $load draft_id (include attachment)

loads a csv of draftees into the draft ***REQUIRES FIRST FIELD TO BE ID AND SECOND FIELD TO BE NAME***

### $execute draft_id round_count

starts the draft

### $list draft_id

lists the draftees available

### $draft draft_id draftee_id

drafts a draftee

### $roster draft_id [member_id]

check your roster, or the roster of the given member
