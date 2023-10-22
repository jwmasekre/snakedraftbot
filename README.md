# snakedraftbot

discord bot for running snake drafts

developed using discord.py and tested exclusively with python 3.12

## questions

### what's a draft

a bunch of people (drafters) take turns selecting entities (draftees) from a pool to build a roster

### what's a snake draft

a type of draft where the turn order for the first round is randomized, and then subsequent rounds are the reverse of the previous round

so-called because the order kinda looks like a snake:

```ascii
round - drafter1 - drafter2 - drafter3 - drafter4
  1  ═╪══════════╪══════════╪══════════╪═══════╗
  2      ╔═══════╪══════════╪══════════╪═══════╝
  3      ╚═══════╪══════════╪══════════╪═══════╗
  4  ◄╪══════════╪══════════╪══════════╪═══════╝
```

for example, a 4 round, 4 member roster might look like this:

|round|1st|2nd|3rd|4th|
|---|---|---|---|---|
|1|alice|bob|carol|dave|
|2|dave|carol|bob|alice|
|3|alice|bob|carol|dave|
|4|dave|carol|bob|alice|

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

## roadmap

1. complete base functionality
2. implement better input validation
3. develop persistence (currently all data is lost when script exits)
4. transparently support multiple servers

## changelog

* 20231011 - first real upload - not fully functional
