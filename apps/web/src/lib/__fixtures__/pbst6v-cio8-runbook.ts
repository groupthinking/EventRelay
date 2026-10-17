import { parseGroundedSpec } from "@/lib/grounded-build-spec";
import { applyExtractedSpec, buildIdentityPack } from "@/lib/video-pack";
import type { ExtractedVideoPackSpec } from "@/lib/video-pack-extractor";

/**
 * Real Video Pack slice for vp:v0:pBsT6v-ciO8 (live GET https://uvai.io/api/video/pack
 * returned 200 on 2026-10-17; source_hash 7112013305897e98ef95e21af0090b9f8793acb01a6d51c1278a6325c2df6d51).
 * Transcript segments, chapters, requirements, action_items, code_snippets,
 * stack.tools, architecture, artifacts, keyframes, visual_context and the
 * grounded_spec candidate are copied verbatim. Nothing here is synthetic;
 * tests that need an unanchored step add their own rows.
 */
export const PBST6V_VIDEO_ID = "pBsT6v-ciO8";
export const PBST6V_SOURCE_HASH = "7112013305897e98ef95e21af0090b9f8793acb01a6d51c1278a6325c2df6d51";

export const PBST6V_RAW_EXTRACT: Omit<ExtractedVideoPackSpec, "grounded_spec"> & {
  grounded_spec: Record<string, unknown>;
} = {
  "transcript": {
    "language": "en",
    "full_text": "What do you think are the three mini gold rushes happening inside AI right now that no one is talking about? Yeah, I would say almost like the last time I was on here, I said that the thing young people should be doing is building AI apps and marketing them. But I realize now that even that is too much work for the average person to do, despite that being like like a completely viable way to make your millions. I think AI video will spawn in a whole new era of labor for people to go out, make AI videos for companies to serve as marketing material, or just completely upend all social medias as we know it, you know, cuz really that like that the way the world happens today is Instagram Reels and TikTok. Functionally, this is where Mamdani gets gets made mayor of New York City, this is where AOC becomes like one of the most famous politicians in America. This is where social media is where things happen, and AI video has the potential to completely upend social media. And the easiest, lowest-effort thing that somebody can do to make their riches, a sub-gold rush of AI, is just AI video. Like go out there and make AI videos, email a bunch of companies: 'Here's a UGC video that that that that I made for you that you made online. Run this as an ad, and if it's not profitable, then don't ever talk to me again. But if it is profitable, then put me on a retainer for $3,000 a month and I'll continue to make you AI ads just like this.' And you can literally sit there and just fucking type in AI some some some bullshit with a million typos and like make make an ad for this company. More broadly, though, I would say the the way to make money with AI today is to capture the value of people who do not know how good AI is right now. There are so many companies like this, so many people like this. In fact, I would say 99.9% of companies in the world today are like this. They have the opportunity to use AI for something that they are not doing. And you, whether that's making ads for them because they're not tapping into AI video enough, whether that's making websites for them because, you know, they're they're not figuring that out enough, whether it's building AI apps and then selling that to the average consumer who doesn't know that they could vibe code this themselves over a weekend—this is where you stand to make your money. And there are so, so many ways to make millions of dollars doing this. There's so many people that I know who have made millions of dollars doing the most absurd things: building the most random apps, doing doing the most random bullshit for for different companies. There's marketing agencies that exist now that subcontract middle schoolers to make AI videos for them and then sell those as ads. Like like this exact process that I talked about: 'I'll make you a bunch of ads for your company, and rather than having, you know, like like an in-house a grand empire of 40 like like a huge building with 40 UGC creators and like like having to go through all all all that nonsense, literally just DM a bunch of 14-year-old TikTokers online, have them make the ads, and sell that to the company.' There's marketing agencies that exist like that today. There's marketing agencies that exist for LinkedIn ghostwriting where you don't do any of the ghostwriting. You just convince someone that you you can make LinkedIn posts for them, and you just generate a bunch of AI random bullshit, and the person that you're selling to doesn't know at all that what what you've just sent them is completely AI-generated and you didn't even look at it, you know? Like for all they know, they're some fucking 45-year-old who doesn't even know what fucking ChatGPT is. There's so many people making money in so many different ways. And if you had to ask me, you know, like like the three subcategories, I'd say the the highest level: If you are the most competent and and and smartest person watching this video, then you probably want to do something that serves the AI labs. You build a company around whether it's, you know, providing them data, you know, building infrastructure for for for for them to run their to run their models on, trying to develop some some some some some sort of a thing that will slightly improve the efficiency of some data chip of of of of of of of of some chip or GPU. Anything in that in that field, it's ripe, it's it's the VC money is is is flowing in that field. Like truly billions, multiple billions to be made there. If you want to build an app, you know, you can you can you you can go out and build apps if you're not interested in in taking a swing at that level. You can build an app, you can market it. It's never been easier to build before, it's never been easier to market before, and you can market it with an AI influencer. You can build an app in an afternoon, get it approved by the App Store in the next 3 days, and you can market it entirely with AI influencers. And in theory, this is all possible. It's possible for you to spawn in a million dollars in a week. You can do that. You can just go on some AI video platform and just figure out like, okay, here's a UGC video that I think would be funny, send it to any company, and be on a retainer and just make 10k a month doing that. There are there's there's just so much so much so much money to be made at so many different levels. Me personally, this it makes me want to go back to every podcast I've done in every podcast I've seen about how to make money with social media and just apply it to AI video specifically, cuz there's a million different ways people have made money with videos on social media, like YouTube agencies that like sell ads for creators, and there's like long-form content, there's short-form content, there's audio content, there's transcribing the videos into other languages so you can make AI videos in other countries. So a lot of stuff like that. There's Facebook ads, UGC content like you said, but if we let's try to distill this down to make it super accessible, and you can take your time on this one. If you had to go from zero to a million dollars in 6 months with AI video, how would you do it? Step one: search up SeaDance 2.5, find any provider. Step two: find 100 software companies who have raised over $10 million in venture capital. Step three: for every single one of them, make a compelling ad, an ad that you think you would watch on social media yourself using SeaDance 2.5. Step four: email every single one of these companies every single day with the ad, telling them 'I made this ad for you for free. Go run it as an ad. If it's profitable, put me on a retainer, I'll make you more ads. If this ad performs for you, pay me $10,000 a month, I will make you more ads just like this and I guarantee I'll make you money. If it's not profitable, completely ignore this email, never talk to me again. But I made this for you for free.' Email them that same thing every single day until they respond. Step five: repeat this eight times, and you have eight clients paying you $10,000 a month, and over a year you make a million dollars. I guess six six months, so sure, repeat it 16 times. Get 16 companies to to sign this off. By the way, this is something that I would sign off on. That would work. I ask people this question a lot, that would work though. Damn. And then just any one bit of advice to add to that on how to make good AI ads? If you are young and interested in making money, one of the only advantages that you have—cuz realistically, on average, you're stupider than the generations before you, on average there's more competitors out there in the space of entrepreneurship than ever before, and one of your only skills that you have is the skill that you spent the last 14 years of your life doom-scrolling 8 hours a day on TikTok or Instagram Reels or YouTube Shorts or whatever kids—and there is actually a way to use that to your advantage, which is you have the unique ability, well I would say even most people watching this video, and I really think the average person watching any video online is some fucking farmer in Kansas that is going to be incapable of doing anything that requires any sort of cognitive ability at all, but genuinely for the average person watching this video, it is possible for them to look at a video and say 'This is boring' or 'This is not.' And that is the only skill that you need to make compelling AI ads or compelling AI videos that will actually work. Because what surprises me almost every single week, at least once a week I have an instance of this surprising me, is these 40-year-old Boomers on Facebook do not understand what's boring. They will genuinely read the most AI slop bullshit ever, the the the the the most disgustingly em-dash filled essay ever, and they'll send it to their grandkids be like 'You should read this, this was inspiring to me.' These people genuinely do not have that sense that you develop over years of, you know, scrolling. And you're a young guy watching the video, you're a young person watching the video, like that sense is genuinely the only thing you need to sit down in front of SeaDance 2.5 and keep prompting something over and over until you get something that you think is funny. Cuz if you think it's funny as a 14-year-old who doom-scrolls, other other 14-year-olds will will find it funny, and you will you you you will have had a video that the the 40-year-olds on Facebook would just never ever ever have been able to make. I think that's good advice, yeah, and I'm realizing now you can also just look up a company, go to their Facebook ads Meta library, whatever, see their longest-running ad, and then remake it with SeaDance. Of course, yes, and and and sell it to their competitors. [Laughter] This is this is good stuff, Roy. I mean, do you think getting rich is just painfully simple in 2026? If this were the 1800s and you wanted to get rich, first of all, you have to pray that you're born in America. Second of all, you have to pray your ass is not Black. Second of all or third of all, you got to pray that, you know, your family has the money to send you to college. Fourth of all, you got to pray that, you know, like you're not fucking doomed to be some coal miner for the rest of your life because your your father was and your grandfather was before you and they don't know anything outside of that and they would fucking beat you and kick you out of the house if you weren't going to be going to participate in the coal mining industry. There's so many loopholes that you had to go through that are literally just chance by genetic lottery. Right now, it is true, it is objectively true, there are more young millionaires now than ever. You could have got lucky on some fucking crypto coin back in, you know, like 4 years ago, and you wouldn't have even had to be 18 years old. You could have fucking KYC'd using your mom's ID, you could have put 20 bucks in it, and you could have fucking flipped this 20 bucks into millions of dollars. And there genuinely are 14, 15, 16-year-olds that have done this before. And perhaps not painfully easy, but getting rich right now compared to the 1800s is both painfully easy and it is painfully simple. You have the entire knowledge of humanity essentially at your fingertips, not just with the internet, but with AI. Because I guarantee if you ask AI 'How can I make $10,000 this month?', the AI will come up with at least one solution that is somewhat viable. And the only difference between the version of you that has made the money and the version of you that is not is that the version of you that has made the money actually tried it. And this is just such a different thing than it was back in the day where if you didn't start the fucking carpentry business that your entire village relied on, then you weren't making it out. Like genuinely, you can just type the right buttons on your laptop and you will become rich, and there's an infinite wealth of advice waiting for you that you don't even have to fucking watch anymore cuz you can just ask AI to summarize the videos for you and it will genuinely tell you the",
    "segments": [
      {
        "idx": 0,
        "start_s": 0,
        "end_s": 6.7,
        "text": "What do you think are the three mini gold rushes happening inside AI right now that no one is talking about? Yeah, I would say almost"
      },
      {
        "idx": 1,
        "start_s": 6.7,
        "end_s": 14.5,
        "text": "like the last time I was on here, I said that the thing young people should be doing is building AI apps and marketing them."
      },
      {
        "idx": 2,
        "start_s": 14.5,
        "end_s": 22.3,
        "text": "But I realize now that even that is too much work for the average person to do, despite that being like like a completely viable way to make your millions."
      },
      {
        "idx": 3,
        "start_s": 22.3,
        "end_s": 35,
        "text": "I think AI video will spawn in a whole new era of labor for people to go out, make AI videos for companies to serve as marketing material, or just completely upend all social medias as we know it, you know, cuz really that like that the"
      },
      {
        "idx": 4,
        "start_s": 35,
        "end_s": 42.6,
        "text": "the way the world happens today is Instagram Reels and TikTok. Functionally, this is where Mamdani gets gets made mayor of New York City, this is where"
      },
      {
        "idx": 5,
        "start_s": 42.6,
        "end_s": 50.8,
        "text": "AOC becomes like one of the most famous politicians in America. This is where social media is where things happen, and AI video has the potential to completely upend social media."
      },
      {
        "idx": 6,
        "start_s": 50.8,
        "end_s": 58.7,
        "text": "And the easiest, lowest-effort thing that somebody can do to make their riches, a sub-gold rush of AI, is just AI video. Like go out there and make AI videos,"
      },
      {
        "idx": 7,
        "start_s": 58.7,
        "end_s": 65.5,
        "text": "email a bunch of companies: 'Here's a UGC video that that that that I made for you that you made online. Run this as an ad, and if it's not profitable,"
      },
      {
        "idx": 8,
        "start_s": 65.5,
        "end_s": 73,
        "text": "then don't ever talk to me again. But if it is profitable, then put me on a retainer for $3,000 a month and I'll continue to make you AI ads just like this.'"
      },
      {
        "idx": 9,
        "start_s": 73,
        "end_s": 77,
        "text": "And you can literally sit there and just fucking type in AI some some some bullshit with a million typos and like make make an ad for this company."
      },
      {
        "idx": 10,
        "start_s": 77,
        "end_s": 85,
        "text": "More broadly, though, I would say the the way to make money with AI today is to capture the value of"
      },
      {
        "idx": 11,
        "start_s": 85,
        "end_s": 93.3,
        "text": "people who do not know how good AI is right now. There are so many companies like this, so many people like this. In fact, I would say 99.9% of companies in the world today are like this."
      },
      {
        "idx": 12,
        "start_s": 93.3,
        "end_s": 102.5,
        "text": "They have the opportunity to use AI for something that they are not doing. And you, whether that's making ads for them because they're not tapping into AI video enough, whether that's making websites for them because, you know, they're they're not figuring that out enough,"
      },
      {
        "idx": 13,
        "start_s": 102.5,
        "end_s": 110,
        "text": "whether it's building AI apps and then selling that to the average consumer who doesn't know that they could vibe code this themselves over a weekend—this is where you stand to make your money."
      },
      {
        "idx": 14,
        "start_s": 110,
        "end_s": 117.8,
        "text": "And there are so, so many ways to make millions of dollars doing this. There's so many people that I know who have made millions of dollars doing the most absurd things: building the most random apps, doing doing the most random bullshit for for different companies."
      },
      {
        "idx": 15,
        "start_s": 117.8,
        "end_s": 125,
        "text": "There's marketing agencies that exist now that subcontract middle schoolers to make AI videos for them and then sell those as ads. Like like this exact process that I talked about:"
      },
      {
        "idx": 16,
        "start_s": 125,
        "end_s": 132,
        "text": "'I'll make you a bunch of ads for your company, and rather than having, you know, like like an in-house a grand empire of 40 like like a huge building with 40 UGC creators and like like having to go through all all all that nonsense,"
      },
      {
        "idx": 17,
        "start_s": 132,
        "end_s": 140,
        "text": "literally just DM a bunch of 14-year-old TikTokers online, have them make the ads, and sell that to the company.' There's marketing agencies that exist like that today."
      },
      {
        "idx": 18,
        "start_s": 140,
        "end_s": 148,
        "text": "There's marketing agencies that exist for LinkedIn ghostwriting where you don't do any of the ghostwriting. You just convince someone that you you can make LinkedIn posts for them, and you just generate a bunch of AI random bullshit,"
      },
      {
        "idx": 19,
        "start_s": 148,
        "end_s": 156,
        "text": "and the person that you're selling to doesn't know at all that what what you've just sent them is completely AI-generated and you didn't even look at it, you know? Like for all they know, they're some fucking 45-year-old who doesn't even know what fucking ChatGPT is."
      },
      {
        "idx": 20,
        "start_s": 156,
        "end_s": 167,
        "text": "There's so many people making money in so many different ways. And if you had to ask me, you know, like like the three subcategories, I'd say the the highest level: If you are the most competent and and and smartest person watching this video,"
      },
      {
        "idx": 21,
        "start_s": 167,
        "end_s": 175,
        "text": "then you probably want to do something that serves the AI labs. You build a company around whether it's, you know, providing them data, you know, building infrastructure for for for for them to run their to run their models on,"
      },
      {
        "idx": 22,
        "start_s": 175,
        "end_s": 183,
        "text": "trying to develop some some some some some sort of a thing that will slightly improve the efficiency of some data chip of of of of of of of of some chip or GPU. Anything in that in that field, it's ripe, it's it's the VC money is is is flowing in that field."
      },
      {
        "idx": 23,
        "start_s": 183,
        "end_s": 191,
        "text": "Like truly billions, multiple billions to be made there. If you want to build an app, you know, you can you can you you can go out and build apps if you're not interested in in taking a swing at that level."
      },
      {
        "idx": 24,
        "start_s": 191,
        "end_s": 198.5,
        "text": "You can build an app, you can market it. It's never been easier to build before, it's never been easier to market before, and you can market it with an AI influencer."
      },
      {
        "idx": 25,
        "start_s": 198.5,
        "end_s": 207,
        "text": "You can build an app in an afternoon, get it approved by the App Store in the next 3 days, and you can market it entirely with AI influencers. And in theory, this is all possible. It's possible for you to spawn in a million dollars in a week."
      },
      {
        "idx": 26,
        "start_s": 207,
        "end_s": 215,
        "text": "You can do that. You can just go on some AI video platform and just figure out like, okay, here's a UGC video that I think would be funny, send it to any company, and be on a retainer and just make 10k a month doing that."
      },
      {
        "idx": 27,
        "start_s": 215,
        "end_s": 223,
        "text": "There are there's there's just so much so much so much money to be made at so many different levels. Me personally, this it makes me want to go back to every podcast I've done in every podcast I've seen about how to make money with social media"
      },
      {
        "idx": 28,
        "start_s": 223,
        "end_s": 231,
        "text": "and just apply it to AI video specifically, cuz there's a million different ways people have made money with videos on social media, like YouTube agencies that like sell ads for creators,"
      },
      {
        "idx": 29,
        "start_s": 231,
        "end_s": 239,
        "text": "and there's like long-form content, there's short-form content, there's audio content, there's transcribing the videos into other languages so you can make AI videos in other countries."
      },
      {
        "idx": 30,
        "start_s": 239,
        "end_s": 247,
        "text": "So a lot of stuff like that. There's Facebook ads, UGC content like you said, but if we let's try to distill this down to make it super accessible, and you can take your time on this one."
      },
      {
        "idx": 31,
        "start_s": 247,
        "end_s": 254.5,
        "text": "If you had to go from zero to a million dollars in 6 months with AI video, how would you do it? Step one: search up SeaDance 2.5, find any provider."
      },
      {
        "idx": 32,
        "start_s": 254.5,
        "end_s": 261,
        "text": "Step two: find 100 software companies who have raised over $10 million in venture capital."
      },
      {
        "idx": 33,
        "start_s": 261,
        "end_s": 268,
        "text": "Step three: for every single one of them, make a compelling ad, an ad that you think you would watch on social media yourself using SeaDance 2.5."
      },
      {
        "idx": 34,
        "start_s": 268,
        "end_s": 275.5,
        "text": "Step four: email every single one of these companies every single day with the ad, telling them 'I made this ad for you for free. Go run it as an ad."
      },
      {
        "idx": 35,
        "start_s": 275.5,
        "end_s": 283,
        "text": "If it's profitable, put me on a retainer, I'll make you more ads. If this ad performs for you, pay me $10,000 a month, I will make you more ads just like this and I guarantee I'll make you money."
      },
      {
        "idx": 36,
        "start_s": 283,
        "end_s": 290.5,
        "text": "If it's not profitable, completely ignore this email, never talk to me again. But I made this for you for free.' Email them that same thing every single day until they respond."
      },
      {
        "idx": 37,
        "start_s": 290.5,
        "end_s": 298,
        "text": "Step five: repeat this eight times, and you have eight clients paying you $10,000 a month, and over a year you make a million dollars."
      },
      {
        "idx": 38,
        "start_s": 298,
        "end_s": 305,
        "text": "I guess six six months, so sure, repeat it 16 times. Get 16 companies to to sign this off. By the way, this is something that I would sign off on."
      },
      {
        "idx": 39,
        "start_s": 305,
        "end_s": 312,
        "text": "That would work. I ask people this question a lot, that would work though. Damn. And then just any one bit of advice to add to that on how to make good AI ads?"
      },
      {
        "idx": 40,
        "start_s": 312,
        "end_s": 321,
        "text": "If you are young and interested in making money, one of the only advantages that you have—cuz realistically, on average, you're stupider than the generations before you, on average there's more competitors out there in the space of entrepreneurship than ever before,"
      },
      {
        "idx": 41,
        "start_s": 321,
        "end_s": 329,
        "text": "and one of your only skills that you have is the skill that you spent the last 14 years of your life doom-scrolling 8 hours a day on TikTok or Instagram Reels or YouTube Shorts or whatever kids—"
      },
      {
        "idx": 42,
        "start_s": 329,
        "end_s": 337,
        "text": "and there is actually a way to use that to your advantage, which is you have the unique ability, well I would say even most people watching this video, and I really think the average person watching any video online is some fucking farmer in Kansas that is going to be incapable of doing anything that requires any sort of cognitive ability at all,"
      },
      {
        "idx": 43,
        "start_s": 337,
        "end_s": 344,
        "text": "but genuinely for the average person watching this video, it is possible for them to look at a video and say 'This is boring' or 'This is not.' And that is the only skill that you need to make compelling AI ads"
      },
      {
        "idx": 44,
        "start_s": 344,
        "end_s": 352,
        "text": "or compelling AI videos that will actually work. Because what surprises me almost every single week, at least once a week I have an instance of this surprising me, is these 40-year-old Boomers on Facebook do not understand what's boring."
      },
      {
        "idx": 45,
        "start_s": 352,
        "end_s": 361,
        "text": "They will genuinely read the most AI slop bullshit ever, the the the the the most disgustingly em-dash filled essay ever, and they'll send it to their grandkids be like 'You should read this, this was inspiring to me.'"
      },
      {
        "idx": 46,
        "start_s": 361,
        "end_s": 368.5,
        "text": "These people genuinely do not have that sense that you develop over years of, you know, scrolling. And you're a young guy watching the video, you're a young person watching the video, like that sense is genuinely the only thing you need to sit down in front of SeaDance 2.5"
      },
      {
        "idx": 47,
        "start_s": 368.5,
        "end_s": 376,
        "text": "and keep prompting something over and over until you get something that you think is funny. Cuz if you think it's funny as a 14-year-old who doom-scrolls, other other 14-year-olds will will find it funny,"
      },
      {
        "idx": 48,
        "start_s": 376,
        "end_s": 384,
        "text": "and you will you you you will have had a video that the the 40-year-olds on Facebook would just never ever ever have been able to make."
      },
      {
        "idx": 49,
        "start_s": 384,
        "end_s": 393,
        "text": "I think that's good advice, yeah, and I'm realizing now you can also just look up a company, go to their Facebook ads Meta library, whatever, see their longest-running ad, and then remake it with SeaDance."
      },
      {
        "idx": 50,
        "start_s": 393,
        "end_s": 401,
        "text": "Of course, yes, and and and sell it to their competitors. [Laughter] This is this is good stuff, Roy. I mean, do you think getting rich is just painfully simple in 2026?"
      },
      {
        "idx": 51,
        "start_s": 401,
        "end_s": 412,
        "text": "If this were the 1800s and you wanted to get rich, first of all, you have to pray that you're born in America. Second of all, you have to pray your ass is not Black. Second of all or third of all, you got to pray that, you know, your family has the money to send you to college."
      },
      {
        "idx": 52,
        "start_s": 412,
        "end_s": 420,
        "text": "Fourth of all, you got to pray that, you know, like you're not fucking doomed to be some coal miner for the rest of your life because your your father was and your grandfather was before you and they don't know anything outside of that and they would fucking beat you and kick you out of the house if you weren't going to be going to participate in the coal mining industry."
      },
      {
        "idx": 53,
        "start_s": 420,
        "end_s": 427,
        "text": "There's so many loopholes that you had to go through that are literally just chance by genetic lottery. Right now, it is true, it is objectively true, there are more young millionaires now than ever."
      },
      {
        "idx": 54,
        "start_s": 427,
        "end_s": 435,
        "text": "You could have got lucky on some fucking crypto coin back in, you know, like 4 years ago, and you wouldn't have even had to be 18 years old. You could have fucking KYC'd using your mom's ID, you could have put 20 bucks in it, and you could have fucking flipped this 20 bucks into millions of dollars."
      },
      {
        "idx": 55,
        "start_s": 435,
        "end_s": 443,
        "text": "And there genuinely are 14, 15, 16-year-olds that have done this before. And perhaps not painfully easy, but getting rich right now compared to the 1800s is both painfully easy and it is painfully simple."
      },
      {
        "idx": 56,
        "start_s": 443,
        "end_s": 451,
        "text": "You have the entire knowledge of humanity essentially at your fingertips, not just with the internet, but with AI. Because I guarantee if you ask AI 'How can I make $10,000 this month?', the AI will come up with at least one solution that is somewhat viable."
      },
      {
        "idx": 57,
        "start_s": 451,
        "end_s": 458,
        "text": "And the only difference between the version of you that has made the money and the version of you that is not is that the version of you that has made the money actually tried it."
      },
      {
        "idx": 58,
        "start_s": 458,
        "end_s": 466,
        "text": "And this is just such a different thing than it was back in the day where if you didn't start the fucking carpentry business that your entire village relied on, then you weren't making it out."
      },
      {
        "idx": 59,
        "start_s": 466,
        "end_s": 474,
        "text": "Like genuinely, you can just type the right buttons on your laptop and you will become rich, and there's an infinite wealth of advice waiting for you that you don't even have to fucking watch anymore cuz you can just ask AI to summarize the videos for you and it will genuinely tell you the"
      }
    ]
  },
  "keyframes": [
    {
      "t_s": 0,
      "image_path": "/api/video/pack/frames/pBsT6v-ciO8/0",
      "desc": "Medium close-up of guest speaker sitting at the podcast table with microphone"
    },
    {
      "t_s": 4,
      "image_path": "/api/video/pack/frames/pBsT6v-ciO8/4",
      "desc": "Interviewer with curly hair asking about three mini AI gold rushes"
    },
    {
      "t_s": 9,
      "image_path": "/api/video/pack/frames/pBsT6v-ciO8/9",
      "desc": "Wide shot showing both host and guest seated across the round wooden table with podcast microphones"
    },
    {
      "t_s": 62,
      "image_path": "/api/video/pack/frames/pBsT6v-ciO8/62",
      "desc": "Guest explaining the cold pitch offering a free AI ad on contingency"
    },
    {
      "t_s": 140,
      "image_path": "/api/video/pack/frames/pBsT6v-ciO8/140",
      "desc": "Guest discussing LinkedIn ghostwriting agencies using AI prompts"
    },
    {
      "t_s": 249,
      "image_path": "/api/video/pack/frames/pBsT6v-ciO8/249",
      "desc": "Interviewer asking the guest for a 0 to $1M in 6 months blueprint using AI video"
    },
    {
      "t_s": 272,
      "image_path": "/api/video/pack/frames/pBsT6v-ciO8/272",
      "desc": "Guest outlining the 5-step SeaDance outreach strategy"
    },
    {
      "t_s": 330,
      "image_path": "/api/video/pack/frames/pBsT6v-ciO8/330",
      "desc": "Guest discussing how doom-scrolling instincts provide taste to judge what is boring"
    },
    {
      "t_s": 403,
      "image_path": "/api/video/pack/frames/pBsT6v-ciO8/403",
      "desc": "Interviewer laughing and summarizing Meta ad library competitor remix strategy"
    },
    {
      "t_s": 435,
      "image_path": "/api/video/pack/frames/pBsT6v-ciO8/435",
      "desc": "Guest comparing modern wealth creation via laptops and AI to 19th century constraints"
    }
  ],
  "concepts": [
    "AI video generation",
    "UGC advertising",
    "cold outreach retainer model",
    "taste and viral video intuition",
    "Meta Ad Library competitor remixing",
    "AI infrastructure vs app development",
    "arbitrage of AI awareness gap"
  ],
  "requirements": [
    {
      "id": "REQ-01",
      "title": "AI Video Generation Tooling",
      "detail": "Use SeaDance 2.5 (or equivalent AI video generation engine) to create user-generated content (UGC) marketing ad video assets.",
      "priority": "high",
      "tags": [
        "ai-video",
        "creative",
        "seadance"
      ]
    },
    {
      "id": "REQ-02",
      "title": "Target Prospect List Building",
      "detail": "Identify 100 venture-backed software companies that have raised over $10 million in venture capital.",
      "priority": "high",
      "tags": [
        "lead-generation",
        "b2b",
        "startups"
      ]
    },
    {
      "id": "REQ-03",
      "title": "Spec Ad Creation and Daily Email Outreach",
      "detail": "Generate a tailored spec ad for each prospect, email it daily offering free test ad usage with a $10,000/month retainer proposal upon positive ROI.",
      "priority": "critical",
      "tags": [
        "sales",
        "outreach",
        "retainer"
      ]
    },
    {
      "id": "REQ-04",
      "title": "Creative Taste and Curation",
      "detail": "Iterate generation prompts until content is compelling and engaging, leveraging internet intuition to filter out boring AI slop.",
      "priority": "medium",
      "tags": [
        "taste",
        "prompt-engineering",
        "curation"
      ]
    }
  ],
  "code_snippets": [
    {
      "path_hint": "scripts/outreach_template.ts",
      "lang": "typescript",
      "content": "interface SpecAdPitch {\n  companyName: string;\n  adVideoUrl: string;\n  retainerAmountUsd: number;\n  generatePitchEmail(): string;\n}"
    },
    {
      "path_hint": "scripts/lead_filter.ts",
      "lang": "typescript",
      "content": "interface CompanyLead {\n  name: string;\n  fundingUsd: number;\n  metaAdLibraryUrl?: string;\n  primaryContactEmail: string;\n}\nfunction filterFundedStartups(leads: CompanyLead[]): CompanyLead[];"
    }
  ],
  "architecture": {
    "summary": "Cold spec AI video agency pipeline: Discover funded software companies, extract creative benchmarks from Meta Ad Library, generate bespoke UGC ads using SeaDance 2.5, run daily persistence outreach, and close $10k/month recurring retainers.",
    "stages": [
      {
        "id": "lead-gen",
        "name": "Target Discovery",
        "description": "Scrape or curate list of 100 software companies with >$10M VC funding."
      },
      {
        "id": "ad-gen",
        "name": "Creative Synthesis",
        "description": "Inspect competitors or existing ads, prompt SeaDance 2.5 for engaging UGC style ads."
      },
      {
        "id": "cold-pitch",
        "name": "Contingent Outreach",
        "description": "Send speculative video ad with no-risk offer: free to test, $10k/mo retainer if profitable."
      },
      {
        "id": "monetization",
        "name": "Retainer Execution",
        "description": "Retain 8 to 16 client accounts to hit $1M annualized revenue run-rate."
      }
    ],
    "mermaid": "graph TD\n  A[Discover 100 Funded Startups] --> B[Analyze Existing Ads on Meta Library]\n  B --> C[Generate UGC Ads via SeaDance 2.5]\n  C --> D[Daily Cold Outreach with Spec Ad]\n  D --> E{Ad Profitable?}\n  E -- Yes --> F[Sign $10k/Month Retainer]\n  E -- No --> G[Drop Lead]"
  },
  "artifacts": [
    {
      "path_hint": "contracts/retainer_agreement.md",
      "purpose": "Sample monthly performance retainer template for AI ad creation",
      "interface": "Markdown document"
    },
    {
      "path_hint": "workflows/ad_production_sop.md",
      "purpose": "SOP for prompting SeaDance 2.5 and evaluating boredom/engagement score",
      "interface": "Markdown SOP"
    }
  ],
  "stack": {
    "tools": [
      {
        "name": "SeaDance 2.5",
        "kind": "ai-video-generator",
        "evidence": "Spoken at 04:52 ('search up SeaDance 2.5, find any provider') and 05:09",
        "check": "sea-dance model search"
      },
      {
        "name": "Meta Ad Library",
        "kind": "research-tool",
        "evidence": "Spoken at 07:53 ('go to their Facebook ads Meta library, whatever, see their longest-running ad')",
        "check": "facebook ad library url lookup"
      },
      {
        "name": "ChatGPT",
        "kind": "llm",
        "evidence": "Spoken at 02:46 ('doesn't even know what fucking ChatGPT is')",
        "check": "chatgpt command check"
      }
    ]
  },
  "chapters": [
    {
      "start": 0,
      "end": 77,
      "topic": "The AI Video Labor Opportunity",
      "key_points": [
        "AI apps require too much labor for the average person",
        "AI video offers a low-effort sub-gold rush to upend social media marketing",
        "UGC style AI ads can be sold to companies on retainer"
      ]
    },
    {
      "start": 77,
      "end": 166,
      "topic": "Capturing the AI Awareness Gap",
      "key_points": [
        "99.9% of businesses do not recognize AI capabilities",
        "Agencies subcontract kids or use AI for ghostwriting without clients knowing",
        "Value capture comes from bridging AI tech to traditional businesses"
      ]
    },
    {
      "start": 166,
      "end": 247,
      "topic": "The Three Levels of AI Opportunity",
      "key_points": [
        "Top tier: serving frontier AI labs (chips, data, infrastructure)",
        "Middle tier: rapid AI app building and influencer marketing",
        "Accessible tier: AI video production and marketing agency services"
      ]
    },
    {
      "start": 247,
      "end": 312,
      "topic": "The $0 to $1M in 6 Months Blueprint",
      "key_points": [
        "Step 1: Access SeaDance 2.5",
        "Step 2: Find 100 software companies with >$10M VC funding",
        "Step 3: Generate bespoke UGC ads for each company",
        "Step 4: Cold email daily offering free ad use with a $10k/mo retainer option",
        "Step 5: Close 16 clients to reach $1M within 6 months"
      ]
    },
    {
      "start": 312,
      "end": 403,
      "topic": "Taste & Competitor Remixing",
      "key_points": [
        "Years of doom-scrolling provide an intuitive filter for what is boring",
        "Boomers fail to recognize dull AI slop",
        "Remake top-performing ads from Meta Ad Library and pitch competitors"
      ]
    },
    {
      "start": 403,
      "end": 474,
      "topic": "Modern Wealth vs Historical Barriers",
      "key_points": [
        "Historical wealth required genetic, geographic, and class lottery",
        "Modern wealth creation is accessible via laptops, internet, and AI",
        "Execution and willingness to try is the main differentiator"
      ]
    }
  ],
  "action_items": [
    {
      "id": "ACT-01",
      "title": "Set up SeaDance 2.5",
      "description": "Locate an AI video platform offering SeaDance 2.5 and configure generation presets.",
      "type": "tooling",
      "difficulty": "easy",
      "priority": null
    },
    {
      "id": "ACT-02",
      "title": "Compile 100 VC-Backed Software Companies",
      "description": "Create a spreadsheet of 100 startups with >$10M in funding and their marketing contacts.",
      "type": "research",
      "difficulty": "medium",
      "priority": null
    },
    {
      "id": "ACT-03",
      "title": "Produce Spec Ads & Outreach",
      "description": "Generate 100 custom UGC ads using Meta Ad Library cues and email prospects daily with the contingency offer.",
      "type": "creative",
      "difficulty": "hard",
      "priority": null
    }
  ],
  "visual_context": {
    "visual_elements": [
      {
        "timestamp": 2,
        "element_type": "podcast-guest",
        "content": "Guest Roy seated on the left wearing a beige button-down shirt speaking into a Shure SM7B microphone",
        "confidence": 0.98
      },
      {
        "timestamp": 5,
        "element_type": "podcast-host",
        "content": "Host seated on the right with blonde curly hair and black t-shirt speaking into a microphone",
        "confidence": 0.98
      },
      {
        "timestamp": 9,
        "element_type": "studio-setup",
        "content": "Round wooden table, drink can, glass water bottle, tablet stand, studio backdrop with shelving",
        "confidence": 0.95
      }
    ],
    "summary": "Two-person in-studio video podcast with professional microphones and warm lighting.",
    "frame_analysis_count": 10
  },
  "grounded_spec": {
    "version": "1",
    "outputClass": "browser-interactive",
    "sourceStatus": "full",
    "confidence": 0.95,
    "limitations": [
      "The video is a podcast discussion; concrete UI designs are not demonstrated on screen.",
      "External video generation APIs (SeaDance 2.5) and email servers are server-dependent and cannot run in-browser without external infrastructure."
    ],
    "app": {
      "name": "AIVideoOutreachTracker",
      "purpose": "Track funded software companies, spec AI video generation status, and cold outreach follow-up cadence."
    },
    "screens": [
      {
        "id": "scr-prospects",
        "name": "Prospect Pipeline",
        "purpose": "List target software companies with >$10M funding and outreach status"
      },
      {
        "id": "scr-ad-builder",
        "name": "Spec Ad Log",
        "purpose": "Record prompts, video review ratings (boring vs compelling), and pitch links"
      }
    ],
    "state": [
      {
        "id": "st-prospect-list",
        "name": "prospects",
        "description": "Array of target companies, funding amount, contact email, and campaign status",
        "persistence": "local"
      },
      {
        "id": "st-ad-entries",
        "name": "adEntries",
        "description": "Log of spec ads created per prospect with boredom check boolean",
        "persistence": "local"
      }
    ],
    "requirements": [
      {
        "id": "G-REQ-01",
        "screenId": "scr-prospects",
        "title": "Filter Prospects by Funding",
        "detail": "Record companies that have raised over $10 million in venture capital.",
        "classification": "observed",
        "required": true,
        "capabilities": [
          "browser-ui",
          "local-state",
          "local-persistence"
        ],
        "rationale": "Directly stated as Step 2 of the 5-step blueprint.",
        "citations": [
          {
            "kind": "transcript",
            "index": 32,
            "videoId": "pBsT6v-ciO8",
            "startSeconds": 254.5,
            "endSeconds": 261,
            "quote": "Step two: find 100 software companies who have raised over $10 million in venture capital."
          }
        ]
      },
      {
        "id": "G-REQ-02",
        "screenId": "scr-ad-builder",
        "title": "Boredom Assessment Flag",
        "detail": "Mark whether an AI ad is deemed boring or compelling prior to sending.",
        "classification": "observed",
        "required": true,
        "capabilities": [
          "browser-ui",
          "local-state"
        ],
        "rationale": "The speaker notes that evaluating if a video is boring is the essential human skill needed.",
        "citations": [
          {
            "kind": "transcript",
            "index": 43,
            "videoId": "pBsT6v-ciO8",
            "startSeconds": 337,
            "endSeconds": 344,
            "quote": "it is possible for them to look at a video and say 'This is boring' or 'This is not.' And that is the only skill that you need to make compelling AI ads"
          }
        ]
      },
      {
        "id": "G-REQ-03",
        "screenId": "scr-prospects",
        "title": "Daily Follow-up Scheduler",
        "detail": "Track daily outreach attempts offering the free ad test and $10,000/month retainer proposal.",
        "classification": "observed",
        "required": true,
        "capabilities": [
          "browser-ui",
          "local-state",
          "local-persistence"
        ],
        "rationale": "Step 4 specifies emailing companies every day with the contingent pitch until response.",
        "citations": [
          {
            "kind": "transcript",
            "index": 34,
            "videoId": "pBsT6v-ciO8",
            "startSeconds": 268,
            "endSeconds": 275.5,
            "quote": "Step four: email every single one of these companies every single day with the ad, telling them 'I made this ad for you for free. Go run it as an ad."
          }
        ]
      }
    ],
    "acceptanceCriteria": [
      {
        "id": "AC-01",
        "requirementId": "G-REQ-01",
        "given": "A user enters a company name with funding of $12M",
        "when": "The user submits the entry",
        "then": "The company is saved in local storage and categorized as qualified target"
      },
      {
        "id": "AC-02",
        "requirementId": "G-REQ-02",
        "given": "A generated ad record",
        "when": "The user marks the ad as 'Boring'",
        "then": "The UI prompts the user to re-generate rather than send"
      }
    ],
    "unresolved": [
      {
        "id": "UNRES-01",
        "requirementIds": [
          "G-REQ-03"
        ],
        "question": "Which email automation protocol or provider should be integrated for daily outbound tracking?",
        "required": false
      }
    ],
    "unsupported": [
      {
        "id": "UNSUP-01",
        "requirementIds": [
          "G-REQ-01",
          "G-REQ-03"
        ],
        "capability": "server",
        "reason": "Automated email dispatching and live VC database scraping require backend servers outside browser-interactive constraints.",
        "required": false
      }
    ]
  }
};

/** Full v0 pack (identity + extract + validated grounded_spec), as stored and served. */
export function pbst6vPackFixture() {
  const raw = JSON.parse(JSON.stringify(PBST6V_RAW_EXTRACT)) as typeof PBST6V_RAW_EXTRACT;
  return applyExtractedSpec(buildIdentityPack(PBST6V_VIDEO_ID), {
    ...raw,
    grounded_spec: parseGroundedSpec(raw.grounded_spec, raw, PBST6V_VIDEO_ID),
  });
}
