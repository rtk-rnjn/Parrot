import discord, random, requests, io, base64, datetime, aiohttp, urllib
from discord.ext import commands
from discord.ext.commands import command, guild_only, bot_has_permissions, cooldown, BucketType
from random import choice
from discord import Embed 
from aiohttp import request
from pygicord import Paginator

_truth = '''
Have you ever flashed someone?
Have you ever sexted anyone?
Have you ever been to a nudist beach? Would you consider going?
Would you ever consider posing for Playboy?
Who has seen you without clothes on?
Have you ever seen a naughty magazine?
Have you ever sent a nude selfie? Who would you reply it to?
Have you ever searched for something dirty on the internet?
Who do you most want to sleep with, out of everyone here?
What's your favorite body part on your partner?
How many people have you kissed?
Have you ever been attracted to the same sex?
When and where was your first kiss? Who was it with?
When did you lose your virginity, and to whom did you lose it?
What's your ultimate sexual fantasy?
Would you go out with an older guy? How old is too old?
Do you sleep in the nude?
How much money would we have to pay you for you to agree to flash your boobs?
Have you ever been in a "friends with benefits" situation?
If you had to go skinny dipping with someone, who in this room would you choose?
If I paid you $100, would you wear your sexiest clothes to class?
Who do you want to make out with the most?
If you had to flash just one person in this room, who would it be?
If you haven't had your first kiss yet, who in this room do you want to have your first kiss with?
Of the people in this room, who would you go out with?
Describe the most attractive thing about each person in this room.
Who here do you think is the best flirt?
Who has the best smile?
Who has the cutest nose?
How about prettiest eyes?
Who's the funniest in this room?
What's one thing you would never do in front of someone you had a crush on?
How often do you check yourself out in the mirror when you're on a date?
Who here do you think would be the best kisser?
Who has the best dance moves?
If you could have one physical feature of someone in this room, what would that be?
What is your wildest fantasy?
How far would you go with someone you just met and will never see again?
Rate me on a scale of 1 to 10, with 10 being the hottest.
If I was a food, what would I be, and how would you eat me?
Would you choose a wild, hot relationship or a calm and stable one?
If you had one week to live and you had to marry someone in this room, who would it be?
If you only had 24 hours to live and you could do anything with anyone in this room, who would it be and what would you do with that person?
What's your biggest turn-on?
And your biggest turn-off?
Would you go out with me if I was the last person on earth?
What's the most flirtatious thing you've ever done?
What's the sexiest thing about [fill in the name of a person in the room]?
If you could go on a romantic date with anyone in this room, who would you pick?
What was a rumor that went around about you?
Have you ever failed a class?
If you had the power to fire one teacher, who would that be?
If you could plan a class prank knowing you'll never get caught, what would the prank be?
Have you ever cheated on a test?
Have you ever had a crush on a teacher? Who?
Who would you take to prom?
Have you ever made out at school?
Who would you never ever want to sit next to in class?
Have you ever been late to class?
What's the most embarrassing thing you've ever done in front of a teacher?
Have you ever stuck gum under a desk?
What do you think is better: tests or essays?
Have you ever eaten lunch by yourself? Why?
If you had to take one class for the rest of your life, what class would it be, and who would the teacher be?
If you wanted to make out on campus, where would you do it?
Have you ever gotten into a fight on school grounds?
What was the worst score you’ve ever gotten on a test?
Have you ever fallen asleep in class?
Have you ever gotten detention or been suspended?
If you were invisible, would you sneak a peek in the other locker room?
If so, who would you be hoping to see?
Who's the hottest teacher at our school?
What's the worst class to have first period?
If you had to take a person from another grade to prom, who would that be?
If you had to delete one app from your phone, which one would it be?
What is your greatest fear in a relationship?
Go around the room and say one positive and one negative thing about each person.
What is one disturbing fact I should know about you?
Have you ever smoked?
Have you ever tried drugs?
What about alcohol?
What's the craziest thing you've done while under the influence?
If you were trapped for three days on an island, who are three people in this room you would bring with you and why?
Would you go to a nude beach?
Who's the most annoying person in this room?
Are you still a virgin?
If you had to marry someone in this room, who would it be?
Do you have hidden piercings or tattoos?
How long was your longest relationship?
If you could have one celebrity follow you on Instagram, who would that be?
You have to delete five people on Instagram. Name them.
Do you want to get married one day?
Do you want to have kids? How many?
Would you ever get into a long-distance relationship?
Describe the person of your dreams.
What would you do if you found out you flunked school?
If your girlfriend or boyfriend broke up with you at school, what would you do?
If you had the power to fire one teacher, who would it be?
Basketball, baseball, or football?
What was your first job?
If you don't have one yet, where would you want to work?
How many hours would you spend online if you didn't have school or homework?
How tall do you want to be?
What's your biggest fear about college?
What are you most excited about?
Would you want your best friend to go to the same college as you?
Would you want your current boyfriend or girlfriend to go to the same college as you?
Who do you think is the hottest celebrity?
What's your dream job?
Do you currently have a crush on anyone?
Describe what your crush looks like.
What is your crush's personality like?
Is there anything about your life you would change?
Who do you hate, and why?
What's your biggest pet peeve?
How many people have you kissed?
What's your biggest turn-on?
If you could date anyone in the world, who would you date?
Would you rather be skinny and hairy or fat and smooth?
Who would you ask to prom if you could choose anyone?
Describe your perfect date.
Would you ever date two people at once if you could get away with it?
You have to delete every app on your except for five. Name the five you would keep.
Have you ever sent out a nude Snapchat?
Have you ever received a nude selfie? Who was it from?
What was your reaction? Like or dislike?
Have you ever gotten mad at a friend for posting an unflattering picture of you?
Have you ever had a crush on a teacher?
Who do you think would make the best kisser? (List a few people for them to choose.)
Have you ever sent someone the wrong text?
Have you ever cursed at your parents? Why?
Who do you think is the cutest person in our class?
What is the most attractive feature on a person?
What the biggest deal-breaker for you?
How far would you go on a first date?
Have you ever regretted something you did to get a crush's attention?
Would you ever be mean to someone if it meant you could save your close friend from embarrassment?
Of the people at our school, who do you think would make the best president?
If we didn't have a dress code, what would you wear to school that you can't wear now?
Describe what makes someone husband or wife material.
If you could make $1 million, would you drop out of school?
What is your worst habit?
What's one thing you do that you don't want anyone to know about?
Do you frequently stalk anyone on social media? Who?
If your crush told you he liked your best friend, what would you do?
What if your best friend told you that she liked your crush?
If you knew your friend's boyfriend was cheating on her, what would you do?
Have you ever told a lie about your best friend to make yourself look better?
What was your first impression of [fill in the name of a person in the room]?
If you had to date someone else's boyfriend, who would it be?
Who's hotter: you or your friend?
Have you ever shared your friend's secret with someone else?
Rate everyone in the room from 1 to 10, with 10 being the hottest.
Would you share a toothbrush with your best friend?
Rate everyone in the room from 1 to 10, with 10 being the best personality.
Have you ever ignored a friend's text? Why did you do it?
Have you ever lied to your best friend?
Would you let a friend cheat on a test?
If your friend asked you to lie for her and you knew you would get in trouble, would you do it?
If one of your friends were cheating with your other friend's boyfriend, what would you do?
Would you ditch your friends if you could become the most popular girl in school?
If you had to choose, who would you stop being friends with?
Name one thing you would change about each person in this room.
If you had to trade your friend in for the celebrity crush of your dreams, which friend would you choose?
What was your first impression of your best friend's boyfriend?
What do you think about him now?
Have you ever thought about ditching your friend for a boy?
If someone asked you what your best friend is like, how would you describe her?
You win a trip and are allowed to bring two people. Who do you pick?
On an overnight trip, would you rather share a bed with your best friend or her boyfriend?
If you could swap one physical feature with your best friend, what would that be?
Have you ever told a secret you were told to keep?
If your best friend had B.O., would you tell her?
What is the most annoying thing about your best friend?
Who do you think your friend should date instead of her current boyfriend?
If she doesn't have a boyfriend, who do you think she should date?
Do you think your friend's boyfriend is hot?
Would you hook up with him if you knew she would never find out?
Have you ever ditched your friend for a boy?
If your friend and your boyfriend were both dying in front of you, who would try to save first?
Who would you hate to see naked?
How long have you gone without a shower?
If you could only text one person for the rest of your life, but you could never talk to that person face-to-face, who would that be?
How long have you gone without brushing your teeth?
What's one thing you would never eat on a first date?
What have you seen that you wish you could unsee?
If you could be reincarnated into anyone's body, who would you want to become?
If you switched genders for the day, what would you do?
What's one food that you will never order at a restaurant?
What's the worst weather to be stuck outside in if all you could wear was a bathing suit?
If your car broke down in the middle of the road, who in this room would be the last person you would call? Why?
What's the most useless piece of knowledge you know?
What did you learn in school that you wish you could forget?
Is it better to use shampoo as soap or soap as shampoo?
If you ran out of toilet paper, would you consider wiping with the empty roll?
What would be the worst part about getting pantsed in front of your crush?
If you could only use one swear word for the rest of your life, which one would you choose?
What's the best thing to say to your friend that would be the worst thing to say to your crush?
Who do you think is the Beyonce of the group?
Would you rather eat dog food or cat food?
If you had nine lives, what would you do that you wouldn't do now?
If you could play a prank on anyone without getting caught, who would you play it on?
What would the prank be?
Have you ever pretended to like a gift? How did you pretend?
Would you rather not shower for a month, or eat the same meal every day for a month?
What animal most closely resembles your eating style?
If you could choose to never sweat for the rest of your life or never have to use the bathroom, which would you choose?
If you could spend every waking moment with your girlfriend or boyfriend, would you?
What is the worst date you’ve ever been on?
Have you ever had a crush on a friend’s boyfriend/girlfriend?
If you had to make out with a boy at school, who would it be?
Would you rather go for a month without washing your hair or go for a day without wearing a bra?
Have you ever asked someone out?
Have you ever had a crush on a person at least 10 years older than you?
Who is the worst kisser you’ve kissed?
What size is your bra?
Do you wear tighty-whities or granny panties?
Do you ever admire yourself in the mirror?
Has a crush ever found out you liked them and turned you down?
Have you ever been stood up on a date?
What’s the most embarrassing thing you’ve done regarding your crush?
Do you secretly love Twilight?
Have you ever wanted to be a cheerleader?
Who is the hottest: Hagrid, Dumbledore, or Dobby?
If you could marry any celebrity, who would it be?
What do you do to get yourself "sexy"?
Who is your current crush?
What hairstyle have you always wanted, but never been willing to try?
What’s the most embarrassing thing you’ve said or done in front of someone you like?
What part of your body do you love, and which part do you hate?
Who is your celebrity crush?
If you could change one thing about your body, what would it be?
Who was your first kiss? Did you like it?
Who are you jealous of?
If you could be another girl at our school, who would you be?
Would you kiss a guy on the first date? Would you do more than that?
Who are the top five cutest guys in our class? Rank them.
How many kids do you want to have in the future?
Who do you hate the most?
If you could go out on a date with a celebrity, who would it be?
If you were stranded on a deserted island, who would you want to be stranded with from our school?
Have you ever flirted with your best friend’s siblings?
Have you ever been dumped? What was the reason for it?
Jock, nerd, or bad guy?
Have you ever had a crush on friend's boyfriend?
Who is your first pick for prom?
What's the sexiest thing about a guy?
What's the sexiest thing about a girl?
What's one physical feature that you would change on yourself if you could?
Would you rather be a guy than a girl? Why?
Describe your dream career.
If you could eat anything you wanted without getting fat, what would that food be?
If you had to do a game show with someone in this room, who would you pick?
Would you go a year without your phone if it meant you could marry the person of your dreams?
You are going to be stuck on a desert island, and you can only bring five things. List them.
If you could only wear one hairstyle for the rest of your life, would you choose curly hair or straight hair?
You have to give up one makeup item for the rest of your life. What is it?
Would you date someone shorter than you?
If someone paid you $1000 to wear your bra outside your shirt, would you do it?
What was the last thing you searched for on your phone?
If you had to choose between going naked or having your thoughts appear in thought bubbles above your head for everyone to read, which would you choose?
Have you ever walked in on your parents doing it?
After you've dropped a piece of food, what's the longest time you've left it on the ground and then ate it?
Have you ever tasted a booger?
Have you ever played Cards Against Humanity with your parents?
What's the first thing you would do if you woke up one day as the opposite sex?
Have you ever peed in the pool?
Who do you think is the worst-dressed person in this room?
Have you ever farted in an elevator?
True or false: You have a crush on [fill in the blank].
Of the people in this room, who do you want to trade lives with?
What are some things you think about when sitting on the toilet?
Did you have an imaginary friend growing up?
Do you cover your eyes during a scary part in a movie?
Have you ever practiced kissing in a mirror?
Did your parents ever give you the “birds and the bees” talk?
What is your guilty pleasure?
What is your worst habit?
Has anyone ever walked in on you when going #2 in the bathroom?
Have you ever had a wardrobe malfunction?
Have you ever walked into a wall?
Do you pick your nose?
Do you sing in the shower?
Have you ever peed yourself?
What was your most embarrassing moment in public?
Have you ever farted loudly in class?
Do you ever talk to yourself in the mirror?
You’re in a public restroom and just went #2, then you realized your stall has no toilet paper. What do you do?
What would be in your web history that you’d be embarrassed if someone saw?
Have you ever tried to take a sexy picture of yourself?
Do you sleep with a stuffed animal?
Do you drool in your sleep?
Do you talk in your sleep?
Who is your secret crush?
Do you think [fill in the name] is cute?
Who do you like the least in this room, and why?
What does your dream boy or girl look like?
What is your go-to song for the shower?
Who is the sexiest person in this room?
How would you rate your looks on a scale of 1 to 10?
Would you rather have sex with [insert name] in secret or not have sex with that person, but everyone thinks you did?
What don't you like about me?
What color underwear are you wearing right now?
What was the last thing you texted?
If you were rescuing people from a burning building and you had to leave one person behind from this room, who would it be?
Do you think you'll marry your current girlfriend/boyfriend?
How often do you wash your undergarments?
Have you ever tasted ear wax?
Have you ever farted and then blamed someone else?
Have you ever tasted your sweat?
What is the most illegal thing you have ever done?
Who is your favorite: Mom or Dad?
Would you trade your sibling in for a million dollars?
Would you trade in your dog for a million dollars?
What is your biggest pet peeve?
If you were allowed to marry more than one person, would you? Who would you choose to marry?
Would you rather lose your sex organs forever or gain 200 pounds?
Would you choose to save 100 people without anyone knowing about it or not save them but have everyone praise you for it?
If you could only hear one song for the rest of your life, what would it be?
If you lost one day of your life every time you said a swear word, would you try not to do it?
Who in this room would be the worst person to date? Why?
Would you rather live with no internet or no A/C or heating?
If someone offered you $1 million to break up with your girlfriend/boyfriend, would you do it?
If you were reborn, what decade would you want to be born in?
If you could go back in time in erase one thing you said or did, what would it be?
Has your boyfriend or girlfriend ever embarrassed you?
Have you ever thought about cheating on your partner?
If you could suddenly become invisible, what would you do?
Have you ever been caught checking someone out?
Have you ever waved at someone thinking they saw you when really they didn't? What did you do when you realized it?
What's the longest time you've stayed in the bathroom, and why did you stay for that long?
What's the most unflattering school picture of you?
Have you ever cried because you missed your parents so much?
Would you rather be caught picking your nose or picking a wedgie?
Describe the strangest dream you've ever had. Did you like it?
Have you ever posted something on social media that you regret?
What is your biggest fear?
Do you pee in the shower?
Have you ever ding dong ditched someone?
The world ends next week, and you can do anything you want (even if it's illegal). What would you do?
Would you wear your shirt inside out for a whole day if someone paid you $100?
What is the most childish thing that you still do?
How far would you go to land the guy or girl of your dreams?
Tell us about a time you embarrassed yourself in front of a crush.
Have you ever kept a library book?
Who is one person you pretend to like, but actually don’t?
What children’s movie could you watch over and over again?
Do you have bad foot odor?
Do you have any silly nicknames?
When was the last time you wet the bed?
How many pancakes have you eaten in a single sitting?
Have you ever accidentally hit something with your car?
If you had to make out with any Disney character, who would it be?
Have you ever watched a movie you knew you shouldn’t?
Have you ever wanted to try LARP (Live Action Role-Play)?
What app on your phone do you waste the most time on?
Have you ever pretended to be sick to get out of something? If so, what was it?
What is the most food you’ve eaten in a single sitting?
Do you dance when you’re by yourself?
Would you have voted for or against Trump?
What song on the radio do you sing with every time it comes on?
Do you sleep with a stuffed animal?
Do you own a pair of footie pajamas?
Are you scared of the dark?
What "as seen on TV" product do you secretly want to buy?
Do you still take bubble baths?
If you were home by yourself all day, what would you do?
How many selfies do you take a day?
What is something you’ve done to try to be ‘cooler’?
When was the last time you brushed your teeth?
Have you ever used self-tanner?
What do your favorite pajamas look like?
Do you have a security blanket?
Have you ever eaten something off the floor?
Have you ever butt-dialed someone?
Do you like hanging out with your parents?
Have you ever got caught doing something you shouldn’t?
What part of your body do you love, and which part do you hate?
Have you ever had lice?
Have you ever pooped your pants?
What was the last R-rated movie you watched?
Do you lick your plate?
What is something that no one else knows about you?
Do you write in a diary?
If you had to choose between dating someone ugly who was good in bed or dating someone hot who was bad in bed, which would you choose?
If you could be invisible, who would you spy on?
Who are the top 5 hottest girls at our school? In our class?
Who in this room would you make out with?
If you could date one of your bro's girlfriends, who would it be?
What your favorite body part?
When was the last time you flexed in the mirror?
Describe your perfect partner.
Have you ever been in love?
Blondes or brunettes?
What turns you on the most?
If your parents hated your girlfriend, would you dump her?
If your girlfriend hated your best friend, what would you do?
Who is your biggest celebrity crush?
Would you take steroids?
Have you ever had a crush on a friend's girlfriend?
Who are you jealous of?
Who do you think is the hottest in our group?
What is your biggest turn-off?
Have you ever been rejected by someone?
If you had to choose between being poor and smart or being rich and dumb, what would you choose?
What have you lied to your partner about?
Have you ever cheated on your partner?
Would you go out with an older woman?
Do you have a crush on someone from another school?
Boxers or briefs?
When was the last time you cried?
Have you ever had a crush on a friend's girlfriend?
If you could make out with someone else's girl, who would it be?
If every time you checked out a girl's body you would gain 5 pounds, how often would you do it?
Have you ever lied about your age?
Have you ever fallen in love at first sight?
If a girl you didn't like had a crush on you, how would you act around her?
What if she was your friend?
What would you do if you found out your girlfriend liked someone else?
If we formed a boy band, who here would make the best lead singer?
'''

_dare = '''
Take an embarrassing selfie and post it as your profile picture.
Remove your socks with your teeth.
Go next door with a measuring cup and ask for a cup of sugar.
Let the group choose an item for you to brush your teeth with.
Write your name on the floor with your tongue.
Stick a Hot Cheeto in your nose, and leave it there for five minutes.
Open your front door and howl like a wolf for 30 seconds.
Let the person to your right put duct tape on any part of your body they choose and rip it off.
Put a bunch of honey on your nose and coat it with flour.
Until the next round, talk super loud, like nobody can hear you.
Call your crush.
Take a shot of pickle juice.
Talk to a pillow like it’s your crush.
Pretend you’re a bird and eat cereal off the floor using only your mouth.
Make out with your hand.
Let someone else style your hair and keep it that way for the rest of the day.
Use a brush like you’re talking into a microphone each time you speak.
Color one of your front teeth black. (Eyeliner works!)
Pick your friend’s nose.
Fake cry.
Make repulsive sounds while eating and drinking.
Cross your eyes when talking.
Talk without closing your mouth.
Act like an animal of the group’s choosing.
Get into a debate with a wall.
Squirt your face with a squirt gun continuously while talking.
See how many grapes you can stuff in your mouth.
Hiccup in between each word.
Burp the alphabet.
Draw on your face with permanent marker.
Dip your sock-covered feet in the toilet, and don't dry them off for the rest of the game.
Eat a spoonful of mustard.
Lift up the couch cushions, and if there is anything under them, you need to put it in your mouth for 10 seconds.
Spin around 10 times and try to walk straight.
Eat a raw egg.
Let the group choose three random things from the refrigerator and mix them together. Then you have to eat the mixture.
Stand up and do jumping jacks until your next turn.
Rub your armpits and then smell your fingers.
Dig through the trash and name everything you find.
Go on Facebook Live and read the back of a shampoo bottle.
Call a 7-Eleven and ask if they’re open.
Stand in the backyard and yell at the top of your lungs, “Nooooo! I was adopted!”
Go outside in the driveway and do the disco without music.
Call a car part store and tell them that you need a part for your Model T.
Take a selfie with the toilet and post it online.
Sniff everyone’s feet and rank them in order of freshest to stinkiest.
Call a NY-style pizza place and ask them what the difference is between NY pizza and “real” pizza.
Open your front door and loudly sing “Hallelujah!”
Go outside and pretend you're cutting the grass with an invisible mower.
Call a pizza place and ask if they use cruelty-free wheat in their dough.
Call your mom and tell her you can't find a girlfriend in a very panicked voice.
Wear your underwear over your pants for the rest of the game.
Call the library and ask if they carry a dictionary that translates British to American.
reply a Snapchat of you pretending to cry because you just found out you were adopted.
Go on Facebook and write "How do you spell "facebook"?" as your status.
Sniff the armpit of the person next to you, and describe what it smells like to the entire group.
Go outside and try to summon the rain.
Sing the "Star-Spangled Banner" in a British accent.
Take a picture of a tampon and post it on Instagram.
Call a random number, and when someone picks up, immediately start singing the national anthem.
Call Target and ask them if they deliver popcorn.
Call McDonald's and ask if they sell Whoppers.
Call a pizza shop and ask if you can return a pizza.
Call a car dealership and ask if they have any horse buggies in stock.
Change your relationship status on Facebook to "it's complicated."
Call Macy's and tell them you're interested in buying them.
Sing instead of speaking for the next two rounds of the game.
Call a random number and sing "Happy Birthday."
Call a Chinese restaurant and ask if they have sushi.
Go outside and pick exactly 40 blades of grass with a pair of tweezers.
Eat a whole piece of paper.
Fill your mouth with water, and each person in the group must tell the funniest joke they know. If you spit up the water, you have to eat a spoonful of dirt.
Tie your hands to your ankles for the rest of the game.
Suck your big toe.
Eat a mouthful of raw pasta.
Dump a bunch of LEGOs on the floor and walk over them with your bare feet.
Write a letter to your doctor describing an embarrassing rash you have, and post it on Facebook.
Go outside and hug a mailbox until at least three passersby have seen you.
Only speak in rhymes for the rest of the game.
Soak a shirt in water, put it in the fridge for 20 minutes, and then wear it.
Trade clothes with the person next to you.
Make a silly face and keep it that way until the next round.
Kneel for an hour.
Let someone wax your back.
Drink water straight from a running faucet for a whole minute.
For the rest of the game, do not say "I."
Make up a rap about koalas.
Call a stranger and tell them a secret.
Allow someone to pour ice down your shirt and pants.
Let each person in the group slap you as hard as they can on your butt.
Walk down the street in your underwear.
Make your ear touch your shoulder for the rest of the game.
Run around outside yelling, “I have lice!”
Stop a car that is going down the street and tell them that their wheels are turning.
Open Facebook, go to the account of the first person you see, and Like every post on their wall going back a full year.
Pick the nose of the person next to you.
Lick a car tire.
Lick the bottom of your shoe.
Jump into a dumpster.
Take a plate of leftovers over to your neighbor, knock on their door, and say, "Welcome to the neighborhood" as if you've never met them before.
Text someone “hey.” Every time they respond, say “hey.” Do this 10 times. For the 11th time, reply with “hi.”
Dip your finger in the toilet, and then kiss that finger.
Make a hand puppet by drawing a face on your hand, and use your hand to say what you want to say.
Let everyone look through your search history for two minutes.
Coat your hands in food coloring and don’t wash them off for 10 minutes.
Skype/FaceTime someone and pick your nose during the conversation.
Remove your underwear and throw it in the garbage.
Lick mayonnaise off of someone's toe.
Let a person in the group put a leash on you and walk you down the street.
Cry like a baby for one full minute.
Call a drug store and ask them which laxative is the most effective. After they answer, ask how many they have.
Give yourself a 10-second manicure. Every nail must be painted.
Brush the teeth of the person sitting next to you.
Text your crush and tell them you love them.
Call a random number and try to flirt with the person who picks up.
Stuff ice inside your bra and leave it there for 60 seconds.
Let everyone rummage through your purse.
Post a really long and serious Facebook status confessing your love for chocolate.
Take your bra off under your shirt and don't put it back on until the end of the game.
Do 10 push-ups.
Run around the house with a pair of underwear on your head.
Use three items in the fridge as lotion.
Let the person to your left do your makeup.
Call a guy of the group's choosing and tell him he's the ugliest person you've ever met.
Lick a doorknob.
Be blindfolded for the rest of the game.
Let each person in the group crack an egg on your head.
Sing everything you say for the rest of the game.
Twerk to an NSYNC song.
Dip a toothbrush into the toilet water and brush your teeth with it.
Let people throw food at you.
Rub mayonnaise in your hair and leave it on for the rest of the game.
Blindfold someone and have them kiss three objects.
Get on your knees and walk like that until the end of the game.
Silently do the macarena.
Give yourself a permanent marker mustache.
Shave one of your arms.
Hold your nose while talking.
Give everyone in the room a hug.
Do as many squats as you can. On the front lawn.
Go outside and hug a tree.
Sing the “I Love You” Barney song.
Eat an ant.
Attempt to breakdance.
Do the worm.
Have a full conversation with yourself in a mirror.
Put your shoes on the wrong feet and keep them there.
Do a hula dance.
Lick the wall.
Sing like an opera singer.
Wear your underwear on the outside of your clothes.
Sing the chorus of your favorite song.
For the next 15 minutes, only speak in baby talk.
Put hot sauce on ice cream and eat it.
Admit on Facebook that you still wear a training bra.
Let someone in the group cut a piece of your hair.
Do 50 sit-ups.
Call Walmart and ask if they do makeovers for prom.
Call a tattoo shop and ask if they can tattoo 30 teardrops on your face.
Run down the street with a wet T-shirt on.
Move across the floor using only your hands.
Film a makeup tutorial and post it to Facebook.
Tweet or update your Facebook status to "I think eggplants are sexy."
Draw a tattoo with marker on your bicep.
Give yourself a mohawk.
Shave off all the hair on one leg.
Put all of your clothes on backward.
Hold hands with the person next to you.
reply a romantic text message to a girl of the group's choosing.
Wear lipstick for the rest of the game.
Eat 10 Oreo cookies that are filled with mayo.
Pluck a single nose hair.
Eat a spoonful of wasabi.
Exchange shirts with the player to your right.
Lick peanut butter off of someone's armpit.
Kiss the person to your right on the back of their neck.
Eat a handful of uncooked rice.
Call a random guy and flirt with him in a girly voice.
Lick the toilet seat.
Tie your shirt up to expose your midriff and twerk.
Take a picture of yourself next to a bra and post it on Instagram.
Write on Facebook: "I'm a size 36 C."
Color your teeth with lipstick.
Wear women's clothing and walk down the street. Then, take a selfie and post it to your social media accounts.
Knock on your neighbor's door and ask if they have a spare condom.
Wet your socks and freeze them.
Post something embarrassing on Facebook for one minute, then delete it.
Walk like a crab for the rest of the game.
Cover your whole face in blush.
Eat a spoonful of sugar and act like you're really hyper.
Call a random girl from your class and tell her you want to break up.
Drink a soda and belch as loudly as possible.
Mix orange juice and milk and drink it.
Trim all of your toenails by biting them.
Put on mascara.
Snapchat a picture of your elbow and caption it: "My favorite part of my body."
Eat a spoonful of hot sauce without drinking anything after.
Tape your mouth shut.
Read two paragraphs from a book of someone’s choice.
Take embarrassing pictures and Snapchat them to people.
Use your feet as your hands, picking up anything you need with your toes.
Lick a dog or cat treat and pretend to thoroughly enjoy it.
Lay on the floor and act like a piece of frying bacon.
Stick your bare foot in the toilet for a minute.
Chug a cup of milk.
Make fart noises with your armpit.
Crack an egg over your head.
Smear peanut butter all over your face for a 30-minute facial.
Hop on one foot wherever you have to go.
Do 20 push-ups.
Make yourself a diaper out of a dishtowel and wear it outside your clothes.
Make a hat out of foil and wear it.
Build a pillow fort and sit in it.
Make a mask on your face using wet toilet paper.
Talk like a robot.
Act like Elvis.
Let the person next to you wax you wherever they want.
Sniff another player’s armpit for 10 seconds.
Give your phone to another player to reply a text message to their contact of choice.
Let the other players go through your phone for a minute.
Let another player throw flour in your face.
Sing a song chosen by the group while eating spoonfuls of peanut butter.
Close your eyes and let your friends put whatever food from the fridge they want in your mouth.
One by one, make up a title for each player's movie about their life.
Let your friends pose you and stay like that until the next round.
Let each player choose one word, then attempt to form a sentence with them and post it to Facebook.
Empty your purse, backpack, or wallet, and let everyone see what you have.
Allow the person to your right to tickle you.
Whoever's name begins with an A in the group must call your parents and tell them what a bad friend you are to them.
Do your best impression of someone in the room and keep going until someone correctly guesses who it is.
Be blindfolded and let someone feed you something.
Someone has to dip their finger in the trash can, and you have to lick it.
Go to the bathroom. The person to your left has to be in there with you the whole time.
Trade socks with the person to your right.
Have the person to your right do 10 squats while you lie underneath them.
Hold hands with the person to your left for the rest of the game.
Hand your phone to the person across from you and let them post whatever they want to your social media accounts.
Take the socks off the feet of the person across from you and wear them like gloves until your next turn.
Serenade the person next to you.
Take a selfie with the person next to you, and post it on social media along with a deep and emotional paragraph about what they mean to you.
Let the person across from you give you a wedgie.
Eat a single spaghetti like in Lady and the Tramp with the person to your left.
Pick up a random book and read it in the most seductive voice you can manage.
Change your Facebook status to “I’m coming . . . I’m coming . . . " Then, one minute later, change it to "I just came.”
You’re in school, and you’ve been a bad student. For the next round, you’re in time-out on someone’s lap.
Someone has to lick peanut butter, chocolate sauce, or whipped cream off your finger, cheek, or somewhere of their choice.
With your eyes closed and the other person or people standing across from you in the room, walk with your hands out. You have to kiss the first person you touch, wherever you touch them.
Take a naked selfie and reply it to your partner.
Take your bra off under your shirt and toss it out the window.
Someone gives you a back massage for one minute while you’re blindfolded. If you like their style, you can choose to kiss them afterward, but without knowing their identity.
You have to keep your hand on the very inner thigh of the person next to you for the next round.
Do your best sexy crawl.
'''


class fun(commands.Cog, name="Fun", description="Parrot gives you huge amount of fun commands, so that you won't get bored."):
	'''Parrot gives you huge amount of fun commands, so that you won't get bored.'''
	def __init__(self, bot):
		self.bot = bot
		
	@command(name='8ball')
	@guild_only()
	@commands.cooldown(1, 5, BucketType.member)
	async def _8ball(self, ctx, *, question:commands.clean_content):
		'''
		8ball Magic, nothing to say much.
		
		Syntax:
		`8ball <Question:Text>`

		Cooldown of 5 seconds after one time use, per member.
		'''
		response = ["All signs point to yes...","Yes!", "My sources say nope.", "You may rely on it.", "Concentrate and ask again...", "Outlook not so good...", "It is decidedly so!", "Better not tell you.", "Very doubtful.", "Yes - Definitely!", "It is certain!", "Most likely.", "Ask again later.", "No!", "Outlook good.", "Don't count on it.", "Why not", "Probably", "Can't say", "Well well..."]
		await ctx.reply(f'Question: **{question}**\nAnswer: **{random.choice(response)}**')


	@commands.command()
	@commands.guild_only()
	@commands.cooldown(1, 5, BucketType.member)
	async def choose(self, ctx, *, options:commands.clean_content):
		'''
		Confuse something with your decision? Let Parrot choose from your choice. 
		
		Syntax:
		`Choose [Option1:Text/Number], [Option2:Text/Number], [Option3:Text/Number], ...`
		
		Cooldown of 5 seconds after one time use, per member.

		NOTE: The `Options` should be seperated by commas `,`.
		'''
		options = options.split(',')
		await ctx.reply(f'{ctx.author.mention} I choose {choice(options)}')
	

	@commands.command(aliases=['colours', 'colour'])
	@commands.guild_only()
	@commands.cooldown(1, 5, BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def color(self, ctx, colour):
		'''
		To get colour information using the hexademical codes.
		
		Syntax:
		`Color <Color:Hexadecimal>`

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Embed Link permission for the bot
		'''
		
		link = f"https://www.thecolorapi.com/id?format=json&hex={colour}"
		async with aiohttp.ClientSession() as session:
			async with session.get(link) as response:
				if response.status == 200:
					res = await response.json()
				else:
					return

		#hex = res['hex']['clean']
		
		#RGB VALUE
		green = round(res['rgb']['fraction']['g'], 2)
		red = round(res['rgb']['fraction']['r'], 2)
		blue = round(res['rgb']['fraction']['b'], 2)
		_green = res['rgb']['g']
		_red = res['rgb']['r']
		_blue = res['rgb']['b']
		
		#HSL VALUE
		hue = round(res['hsl']['fraction']['h'], 2)
		saturation = round(res['hsl']['fraction']['s'], 2)
		lightness = round(res['hsl']['fraction']['l'], 2)
		_hue = res['hsl']['h']
		_saturation = res['hsl']['s']
		_lightness = res['hsl']['l']
		
		#HSV VALUE
		hue_ = round(res['hsv']['fraction']['h'], 2)
		saturation_ = round(res['hsv']['fraction']['s'], 2)
		value_ = round(res['hsv']['fraction']['v'], 2)
		_hue_ = res['hsv']['h']
		_saturation_ = res['hsv']['s']
		_value_ = res['hsv']['v']
		
		#GENERAL
		name = res['name']['value']
		close_name_hex = res['name']['closest_named_hex']
		exact_name = res['name']['exact_match_name']
		distance = res['name']['distance']

		embed = discord.Embed(title="Parrot colour prompt", timestamp=datetime.datetime.utcnow(), colour = discord.Color.from_rgb(_red, _green, _blue), description=f"Colour name: `{name}` | Close Hex code: `{close_name_hex}` | Having exact name? `{exact_name}` | Distance: `{distance}`")
		embed.set_thumbnail(url=f"https://some-random-api.ml/canvas/colorviewer?hex={colour}")
		embed.set_footer(text=f"{ctx.author.name}")
		feilds = [
			("RGB value (fraction)", f"Red: `{_red}` (`{red}`)\nGreen: `{_green}` (`{green}`)\nBlue: `{_blue}` (`{blue}`)", True),
			("HSL value (fraction)", f"Hue: `{_hue}` (`{hue}`)\nSaturation: `{_saturation}` (`{saturation}`)\nLightness: `{_lightness}` (`{lightness}`)", True),
			("HSV value (fraction)", f"Hue: `{_hue_}` (`{hue_}`)\nSaturation: `{_saturation_}` (`{saturation_}`)\nValue: `{_value_}` (`{value_}`)", True)		
			]
		for name, value, inline in feilds:
			embed.add_field(name=name, value=value, inline=inline)
		await ctx.reply(embed=embed)
			
	
	@command()
	@commands.guild_only()
	@commands.cooldown(1, 5, BucketType.member)
	@bot_has_permissions(embed_links=True)
	async def decode(self, ctx, *, string:str):
		'''
		Decode the code to text from Base64 encryption
		
		Syntax:
		`Decode <Base64:Text>`

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Embed Link permission for the bot
		'''
		base64_string = string
		base64_bytes = base64_string.encode("ascii") 
		
		sample_string_bytes = base64.b64decode(base64_bytes) 
		sample_string = sample_string_bytes.decode("ascii") 
		
		embed = discord.Embed(title="Decoding...", colour=discord.Colour.red())
		embed.add_field(name="Encoded text:", value=f'```\n{base64_string}\n```', inline=False)
		embed.add_field(name="Decoded text:", value=f'```\n{sample_string}\n```', inline=False)
		embed.set_thumbnail(url='https://upload.wikimedia.org/wikipedia/commons/4/45/Parrot_Logo.png')
		embed.set_footer(text=f"{ctx.author.name}", icon_url=f'{ctx.author.avatar_url}')
		await ctx.reply(embed=embed)



	@command()
	@bot_has_permissions(embed_links=True)
	@commands.guild_only()
	@commands.cooldown(1, 5, BucketType.member)
	async def encode(self, ctx, *, string:str):
		'''
		Encode the text to Base64 Encryption and in Binary
		
		Syntax:
		`Encode <Text:Text>`
		
		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Embed Link permission for the bot
		'''
		sample_string = string
		sample_string_bytes = sample_string.encode("ascii") 
		res = ''.join(format(ord(i), 'b') for i in string)
		base64_bytes = base64.b64encode(sample_string_bytes) 
		base64_string = base64_bytes.decode("ascii") 
		
		embed = discord.Embed(title="Encoding...", colour=discord.Colour.red())
		embed.add_field(name="Normal [string] text:", value=f'```\n{sample_string}\n```', inline=False)
		embed.add_field(name="Encoded [base64]:", value=f'```\n{base64_string}\n```', inline=False)
		embed.add_field(name="Encoded [binary]:", value=f'```\n{str(res)}\n```', inline=False)
		embed.set_thumbnail(url='https://upload.wikimedia.org/wikipedia/commons/4/45/Parrot_Logo.png')
		embed.set_footer(text=f"{ctx.author.name}", icon_url=f'{ctx.author.avatar_url}')
		await ctx.reply(embed=embed)

	
			
	@command(name="fact")
	@commands.cooldown(1, 5, BucketType.member)
	@bot_has_permissions(embed_links=True)
	@commands.guild_only()
	async def animal_fact(self, ctx, animal: str):
		'''
		Return a random Fact. It's useless command, I know
		
		Syntax:
		`Fact <Animal:Text>`

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Embed Link permission for the bot

		NOTE: Available animals - Dog, Cat, Panda, Fox, Bird, Koala
		'''
		if (animal := animal.lower()) in ("dog", "cat", "panda", "fox", "bird", "koala"):
			fact_url = f"https://some-random-api.ml/facts/{animal}"
			image_url = f"https://some-random-api.ml/img/{'birb' if animal == 'bird' else animal}"

			async with request("GET", image_url, headers={}) as response:
				if response.status == 200:
					data = await response.json()
					image_link = data["link"]

				else:
					image_link = None

			async with request("GET", fact_url, headers={}) as response:
				if response.status == 200:
					data = await response.json()

					embed = Embed(title=f"{animal.title()} fact", description=data["fact"], colour=ctx.author.colour)
					if image_link is not None:
						embed.set_image(url=image_link)
					await ctx.reply(embed=embed)

				else:
					await ctx.reply(f"{ctx.author.mention} API returned a {response.status} status.")

		else:
			await ctx.reply(f"{ctx.author.mention} no facts are available for that animal. Available animals: `dog`, `cat`, `panda`, `fox`, `bird`, `koala`")


	@commands.command()
	@commands.guild_only()
	@commands.cooldown(1, 5, BucketType.member)
	@commands.bot_has_permissions(attach_files=True, embed_links=True)
	async def gay(self, ctx, member:discord.Member=None):
		"""
		Image Generator. Gay Pride.

		Syntax:
		`Gay [User:Mention/ID]`

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Attach Files and Embed Links permissions for the bot.
		"""
		if member is None: member = ctx.author
		async with aiohttp.ClientSession() as wastedSession:
				async with wastedSession.get(f'https://some-random-api.ml/canvas/gay?avatar={member.avatar_url_as(format="png", size=1024)}') as wastedImage: # get users avatar as png with 1024 size
						imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
						
						await wastedSession.close() # closing the session and;
						
						await ctx.reply(file=discord.File(imageData, 'gay.png')) # replying the file


	@commands.command()
	@commands.guild_only()
	@commands.bot_has_permissions(attach_files=True, embed_links=True)
	@commands.cooldown(1, 5, BucketType.member)
	async def glass(self, ctx, member:discord.Member=None):
		'''
		Provide a glass filter on your profile picture, try it!
		
		Syantax:
		`Glass [User:Mention/ID]`

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Embed Link and Attach Files permissions for the bot.
		'''
		if member is None: member = ctx.author
		async with aiohttp.ClientSession() as wastedSession:
				async with wastedSession.get(f'https://some-random-api.ml/canvas/glass?avatar={member.avatar_url_as(format="png", size=1024)}') as wastedImage: # get users avatar as png with 1024 size
						imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
						
						await wastedSession.close() # closing the session and;
						
						await ctx.reply(file=discord.File(imageData, 'glass.png')) # replying the file


	@commands.command()
	@commands.guild_only()
	@commands.cooldown(1, 5, BucketType.member)
	@commands.bot_has_permissions(attach_files=True, embed_links=True)
	async def horny(self, ctx, member:discord.Member=None):
		"""
		Image generator, Horny card generator.
		
		Syntax:
		`Horny [User:Mention/ID]`

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Embed Link and Attach Files permission for the bot
		"""
		if member is None: member = ctx.author
		async with aiohttp.ClientSession() as wastedSession:
				async with wastedSession.get(f'https://some-random-api.ml/canvas/horny?avatar={member.avatar_url_as(format="png", size=1024)}') as wastedImage: # get users avatar as png with 1024 size
						imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
						
						await wastedSession.close() # closing the session and;
						
						await ctx.reply(file=discord.File(imageData, 'horny.png')) # replying the file


	@commands.command(aliases=['insult'])
	@commands.guild_only()
	@commands.cooldown(1, 5, BucketType.member)
	async def roast(self, ctx, member: discord.Member = None):
		'''
		Insult your enemy, Ugh!
		
		Syntax:
		`Roast <User:Mention/ID>`
		
		Cooldown of 5 seconds after one time use, per member
		'''
		if member == None: member = ctx.author
		async with aiohttp.ClientSession() as session:
			async with session.get("https://insult.mattbas.org/api/insult") as response:
				insult = await response.text()
				await ctx.reply(f"**{member.name}** {insult}")



	@commands.command(aliases=['its-so-stupid'])
	@commands.guild_only()
	@commands.cooldown(1, 5, BucketType.member)
	@commands.bot_has_permissions(attach_files=True, embed_links=True)
	async def itssostupid(self, ctx, *, comment:str):
		"""
		:| I don't know what is this, I think a meme generator.
		
		Syntax:
		`Itssostupid <Comment:Text>`

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Embed Link and Attach Files permissions for the bot.
		"""
		member = ctx.author
		if len(comment) > 20: comment = comment[:19:]
		async with aiohttp.ClientSession() as wastedSession:
				async with wastedSession.get(f'https://some-random-api.ml/canvas/its-so-stupid?avatar={member.avatar_url_as(format="png", size=1024)}&dog={comment}') as wastedImage: # get users avatar as png with 1024 size
						imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
						
						await wastedSession.close() # closing the session and;
						
						await ctx.reply(file=discord.File(imageData, 'itssostupid.png')) # replying the file

			

	@commands.command()
	@commands.bot_has_permissions(attach_files=True, embed_links=True)
	@commands.guild_only()
	@commands.cooldown(1, 5, BucketType.member)
	async def jail(self, ctx, member:discord.Member=None):
		"""
		Image generator. Makes you behind the bars. Haha
		
		Syntax:
		`Jail [User:Mention/ID]`

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Embed Link and Attach Files permissions for the bot.
		"""
		if member is None: member = ctx.author
		async with aiohttp.ClientSession() as wastedSession:
				async with wastedSession.get(f'https://some-random-api.ml/canvas/jail?avatar={member.avatar_url_as(format="png", size=1024)}') as wastedImage: # get users avatar as png with 1024 size
						imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
						
						await wastedSession.close() # closing the session and;
						
						await ctx.reply(file=discord.File(imageData, 'jail.png')) # replying the file
	

	@commands.command()
	@commands.bot_has_permissions(attach_files=True, embed_links=True)
	@commands.guild_only()
	@commands.cooldown(1, 5, BucketType.member)
	async def lolice(self, ctx, member:discord.Member=None):
		"""
		This command is not made by me. :\
		
		Syntax:
		`Lolice [User:Mention/ID]`

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Embed Link and Attach Files permissions for the bot.
		"""
		if member is None: member = ctx.author
		async with aiohttp.ClientSession() as wastedSession:
				async with wastedSession.get(f'https://some-random-api.ml/canvas/lolice?avatar={member.avatar_url_as(format="png", size=1024)}') as wastedImage: # get users avatar as png with 1024 size
						imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
						
						await wastedSession.close() # closing the session and;
						
						await ctx.reply(file=discord.File(imageData, 'lolice.png')) # replying the file
	

			
			
	@commands.command(name='meme')
	@commands.guild_only()
	@commands.bot_has_permissions(embed_links=True)
	@commands.cooldown(1, 5, BucketType.member)
	async def meme(self, ctx):
		'''
		Random meme generator.
		
		Syntax:
		`Meme`

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Embed Link permission for the bot
		'''
		link = "https://memes.blademaker.tv/api?lang=en"
		async with aiohttp.ClientSession() as session:
			async with session.get(link) as response:
				if response.status == 200:
					res = await response.json()
				else:
					return
		title = res['title']
		ups = res["ups"]
		downs = res["downs"]
		sub = res["subreddit"]

		embed = discord.Embed(title=f'{title}', discription=f"{sub}")
		embed.set_image(url = res["image"])
		embed.set_footer(text=f"UP(s): {ups} | DOWN(s): {downs}") 

		await ctx.reply(embed=embed)
			

	@commands.command()
	@commands.cooldown(1, 5, BucketType.member)
	@commands.guild_only()
	@commands.bot_has_permissions(embed_links=True)
	async def fakepeople(self, ctx):
		'''
		Fake Identity generator.
		
		Syntax:
		`Fakepeople`

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Embed Link permission for the bot
		'''
		link = "https://randomuser.me/api/"
		async with aiohttp.ClientSession() as session:
			async with session.get(link) as response:
				if response.status == 200:
					res = await response.json()
				else:
					return
		res = res['results'][0]
		name = f"{res['name']['title']} {res['name']['first']} {res['name']['last']}"
		address = f"{res['location']['street']['number']}, {res['location']['street']['name']}, {res['location']['city']}, {res['location']['state']}, {res['location']['country']}, {res['location']['postcode']}"
		cords = f"{res['location']['coordinates']['latitude']}, {res['location']['coordinates']['longitude']}"
		tz = f"{res['location']['timezone']['offset']}, {res['location']['timezone']['description']}"
		email = res['email']
		usrname = res['login']['username']
		pswd = res['login']['password']
		age = res['dob']['age']
		phone = f"{res['phone']}, {res['cell']}"
		pic = res['picture']['large']

		em = discord.Embed(title=f"{name}", description=f"```\n{address}\n{cords}```", timestamp=datetime.datetime.utcnow())
		em.add_field(name="Timezone", value=f"```\n{tz}```", inline=True)
		em.add_field(name="Email & Password", value=f"```\nUsername: {usrname}\nEmail: {email}\nPassword: {pswd}```", inline=True)
		em.add_field(name="Age", value=f"```\n{age}```", inline=True)
		em.set_thumbnail(url=pic)
		em.add_field(name="Phone", value=f"```\n{phone}```", inline=True)
		em.set_footer(text=f"{ctx.author.name}")

		await ctx.reply(embed=em)


	#@commands.command()
	#@commands.cooldown(1, 5, BucketType.member)
	#@commands.guild_only()
	#async def parrot(self, ctx, query:commands.clean_content=None):
	#	'''
	#	Talk with Parrot, it is a small cleverbot integration.
	#
	#	Syntax:
	#	`Parrot <Query:Text>`
	#
	#	Cooldown of 5 seconds after one time use, per member.
	#	'''
	#
	#	if query is None:
	#		await ctx.reply(f"{ctx.author.mention} -> Ask a question!")
	#	try:
	#		if "tu" in query.lower().split(" "): return
	#		if "kya" in query.lower().split(" "): return
	#		if "kar" in query.lower().split(" "): return
	#		if "chal" in query.lower().split(" "): return
	#		if "bhai" in query.lower().split(" "): return
	#		if "pagal" in query.lower().split(" "): return
	#	except:
	#		return await ctx.reply(f"{ctx.author.mention} -> I don't understand!")
	#	link = f"https://vxrl.xyz/api/cleverbot/ask/ai/{query}"
	#	req = requests.get(link).content
	#	text = str(req)
	#	await ctx.reply(f"{ctx.author.mention} -> {text[2:-1:]}")

	@commands.command()
	@commands.bot_has_permissions(attach_files=True, embed_links=True)
	@commands.cooldown(1, 5, BucketType.member)
	@commands.guild_only()
	async def simpcard(self, ctx, member:discord.Member=None):
		"""
		Good for those, who are hell simp! LOL
		
		Syntax:
		`Simpcard [User:Mention/ID]`

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Embed Link and Attach Files permissions for the bot
		"""
		if member is None: member = ctx.author
		async with aiohttp.ClientSession() as wastedSession:
				async with wastedSession.get(f'https://some-random-api.ml/canvas/simpcard?avatar={member.avatar_url_as(format="png", size=1024)}') as wastedImage: # get users avatar as png with 1024 size
						imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
						
						await wastedSession.close() # closing the session and;
						
						await ctx.reply(file=discord.File(imageData, 'simpcard.png')) # replying the file
			
	
	@command(name="slap", aliases=["hit"])
	@commands.guild_only()
	@commands.bot_has_permissions(manage_messages=True)
	@commands.cooldown(1, 5, BucketType.member)
	async def slap_member(self, ctx, member: discord.Member, *, reason: commands.clean_content = "for no reason"):
		'''
		Slap virtually with is shit command.
		
		Syntax:
		`Slap <User:Mention/ID> [Reason:Text]`
		(Default reason is "for no reason")

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Manage Messages permission for the bot
		'''
		await ctx.message.delete()
		await ctx.reply(f"{ctx.author.display_name} slapped {member.mention} {reason}!")
	
		
	@commands.command(aliases=['trans'])
	@commands.guild_only()
	@commands.bot_has_permissions(embed_links=True)
	@commands.cooldown(1, 5, BucketType.member)
	async def translate(self, ctx, from_lang:str, to_lang:str, *, text:str):
		"""
		This command is useful, to be honest, if and only if you use correctly, else it gives error. Not my fault.
		
		Syntax:
		`Translate <From:Text> <To:Text> <Text:Text>`

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Embed Links permission for the bot
		"""
		from_lang = urllib.parse.quote(from_lang)
		to_lang = urllib.parse.quote(to_lang)
		text = urllib.parse.quote(text)
		link = 'https://api.mymemory.translated.net/get?q=' + text + '&langpair=' + from_lang + '|' + to_lang
		async with aiohttp.ClientSession() as session:
			async with session.get(link) as response:
				if response.status == 200:
					res = await response.json()
				else:
					return

		trans_text = res['responseData']['translatedText']

		embed = discord.Embed(title="Translated!!", description=f"Translation: {trans_text}")
		embed.set_footer(text=f"{ctx.author.name}")
		await ctx.reply(embed=embed)
		

	@commands.command(aliases=['triggered'])
	@commands.bot_has_permissions(attach_files=True, embed_links=True)
	@commands.cooldown(1, 5, BucketType.member)
	@commands.guild_only()
	async def trigger(self, ctx, member:discord.Member=None):
		"""
		User Triggered!

		Syntax:
		`Trigger [User:Mention/ID]`

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Embed Links and Attach Files permissions for the bot
		"""
		if member is None: member = ctx.author
		async with aiohttp.ClientSession() as wastedSession:
				async with wastedSession.get(f'https://some-random-api.ml/canvas/triggered?avatar={member.avatar_url_as(format="png", size=1024)}') as wastedImage: # get users avatar as png with 1024 size
						imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
						
						await wastedSession.close() # closing the session and;
						
						await ctx.reply(file=discord.File(imageData, 'triggered.gif')) # replying the file



	@commands.command(aliases=['def', 'urban'])
	@commands.guild_only()
	@commands.cooldown(1, 5, BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def urbandictionary(self, ctx, *, text:str):
		'''
		LOL. This command is insane.
		
		Syntax:
		`Urbandictionary <Query:Text>`

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Embed Links permission for the bot
		'''
		t = text
		text = urllib.parse.quote(text)
		link = 'http://api.urbandictionary.com/v0/define?term=' + text 

		async with aiohttp.ClientSession() as session:
			async with session.get(link) as response:
				if response.status == 200:
					res = await response.json()
				else:
					return
		if res['list'] == []: return await ctx.reply(f"{ctx.author.mention} :\ **{t}** means nothings. Try something else")
		em_list = []
		for i in range(0, len(res['list'])):
			_def = res['list'][i]['definition']
			_link = res['list'][i]['permalink']
			thumbs_up = res['list'][i]['thumbs_up']
			thumbs_down = res['list'][i]['thumbs_down']
			author = res['list'][i]['author']
			example = res['list'][i]['example']
			word = res['list'][i]['word'].capitalize()	
			embed = discord.Embed(title=f"{word}", description=f"{_def}", url=f"{_link}")
			embed.add_field(name="Example", value=f"{example}")
			embed.set_author(name=f"Author: {author}")
			embed.set_footer(text=f"👍 {thumbs_up} | 👎 {thumbs_down}")
			em_list.append(embed)

		paginator = Paginator(pages=em_list, timeout=60.0)
		
		await paginator.start(ctx)


	@commands.command()
	@commands.bot_has_permissions(attach_files=True, embed_links=True)
	@commands.guild_only()
	@commands.cooldown(1, 5, BucketType.member)
	async def wasted(self, ctx, member:discord.Member=None):
		"""
		Overlay 'WASTED' on your profile picture, just like GTA:SA
		
		Syntax:
		`Wasted [User:Mention/ID]`

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Embed Links and Attach Files permissions for the bot
		"""
		if member is None: member = ctx.author
		async with aiohttp.ClientSession() as wastedSession:
				async with wastedSession.get(f'https://some-random-api.ml/canvas/wasted?avatar={member.avatar_url_as(format="png", size=1024)}') as wastedImage: # get users avatar as png with 1024 size
						imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
						
						await wastedSession.close() # closing the session and;
						
						await ctx.reply(file=discord.File(imageData, 'wasted.png')) # replying the file
	

	@commands.command(aliases=['youtube-comment'])
	@commands.bot_has_permissions(attach_files=True, embed_links=True)
	@commands.guild_only()
	async def ytcomment(self, ctx, *, comment:str):
		'''
		Makes a comment in YT. Best ways to fool your fool friends. :')
		
		Syntax:
		`Ytcomment <Comment:Text>`

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Embed Links and Attach Files permissions for the bot
		'''
		member = ctx.author
		if len(comment) > 1000: comment = comment[:999:]
		if len(member.name) > 20: name = member.name[:20:]
		else: name = member.name
		async with aiohttp.ClientSession() as wastedSession:
				async with wastedSession.get(f'https://some-random-api.ml/canvas/youtube-comment?avatar={member.avatar_url_as(format="png", size=512)}&username={name}&comment={comment}') as wastedImage: # get users avatar as png with 1024 size
						imageData = io.BytesIO(await wastedImage.read()) # read the image/bytes
						
						await wastedSession.close() # closing the session and;
						
						await ctx.reply(file=discord.File(imageData, 'ytcomment.png')) # replying the file
	
	
	@commands.command() 
	@commands.guild_only()
	@commands.cooldown(1, 5, BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def dare(self, ctx, member:discord.Member=None):
		"""
		I dared you to use this command.
		
		Syntax:
		`Dare [User:Mention/ID]`

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Embed Links permission for the bot
		"""
		dare = _dare.split("\n")
		if member is None:
			em = discord.Embed(title="Dare", description=f"{random.choice(dare)}", timestamp=datetime.datetime.utcnow())
		else:
			em = discord.Embed(title=f"{member.name} Dared", description=f"{random.choice(dare)}", timestamp=datetime.datetime.utcnow())
		
		em.set_footer(text=f'{ctx.author.name}')
		await ctx.reply(embed=em)


	@commands.command() 
	@commands.guild_only()
	@commands.cooldown(1, 5, BucketType.member)
	@commands.bot_has_permissions(embed_links=True)
	async def truth(self, ctx, member:discord.Member=None):
		"""
		Truth: Who is your crush?
		
		Syntax:
		`Truth [User:Mention/ID]`

		Cooldown of 5 seconds after one time use, per member.

		Permissions:
		Need Embed Links permission for the bot
		"""
		t = _truth.split("\n")
		if member is None:
			em = discord.Embed(title="Truth", description=f"{random.choice(t)}", timestamp=datetime.datetime.utcnow())
			em.set_footer(text=f'{ctx.author.name}')
		else:
			em = discord.Embed(title=f"{member.name} reply!", description=f"{random.choice(t)}", timestamp=datetime.datetime.utcnow())
			em.set_footer(text=f'{ctx.author.name}')
		await ctx.reply(embed=em)


def setup(bot):
	bot.add_cog(fun(bot))
