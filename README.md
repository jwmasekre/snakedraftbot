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

runs a test draft (only works with one draft member for now)

### $testmsg

test message

### $initiate draft_name [opt-in]

starts a draft; if opt-in is not included, all non-bots are auto-added to the member list

### $opt_in draft_name

opt in to a draft

### $opt_out draft_name

opt out of a draft

### $cancel draft_name

cancels a draft

### $load draft_name [test] (include attachment)

loads a csv of draftees into the draft ***REQUIRES FIRST FIELD TO BE ID AND SECOND FIELD TO BE NAME***

don't use `test`, that's used exclusively for [$test](#test)

### $execute draft_name round_count

starts the draft

### $draftlist draft_name

lists the draftees available

### $draft draft_name draftee_id

drafts a draftee

### $roster draft_name [member_id]

check your roster, or the roster of the given member

### $backup

backs up the current draft registry to the server

### $help [command]

provides info, supports help for commands as well

## roadmap

1. ~~complete base functionality~~
2. test the everloving shit out of it
3. implement better input validation
4. ~~develop persistence (currently all data is lost when script exits)~~
5. transparently support multiple servers
6. ~~add logging~~
7. improve logging

## changelog

* 20231107 - added presence and a logo
* 20231106 - tested a bunch, added the backup feature, seems to work as intended, i'm positive flaws exist still
* 20231028 - """100% completion""", ready for testing
* 20231011 - first real upload - not fully functional
