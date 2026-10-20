/// The bundled Look Again cases. Each description mixes the detail that
/// decides the answer with ordinary details that only look suspicious, so the
/// game trains looking, not keyword matching. To add an image case, put the
/// image in the asset catalog and set `imageName`.
enum PracticeBank {
    static let questions: [PracticeQuestion] = ai + edited + real + misleading

    private static let ai: [PracticeQuestion] = [
        PracticeQuestion(
            id: "ai-rally",
            author: "Southside Organizers",
            handle: "southsideorg.example",
            posted: "2h",
            caption: "Six blocks deep and still coming. Thank you all for showing up today.",
            imageDescription: "Wide shot of a packed street rally at dusk. The stage lights flare a little. Toward the back, faces are smooth and evenly lit with no features. A sign on the left reads “FUND OUR SCHOLS NWO”.",
            answer: .ai,
            explanation: "Lens flare is normal for stage lights. The crowd is the problem: a camera blurs distant faces, it doesn't erase them into smooth, evenly lit shapes. Garbled lettering on background signs is still common in generated images.",
            clues: ["Distant faces erased, not blurred", "Garbled lettering on a background sign"]
        ),
        PracticeQuestion(
            id: "ai-cabin",
            author: "Trail Notes",
            handle: "trailnotes.example",
            posted: "5h",
            caption: "Found this little cabin on the ridge trail this morning. Unreal light.",
            imageDescription: "A log cabin in a misty pine forest at sunrise. Sunbeams come through the trees from the upper left. The porch is brightly lit from the right, and the cabin's shadow falls toward the sunbeams.",
            answer: .ai,
            explanation: "Mist and sunbeams are ordinary at sunrise. But one sun can't light the porch from the opposite side, or cast a shadow back toward itself. Generators often get lighting right in each part of a picture and wrong across the whole.",
            clues: ["Light coming from two directions", "Shadow falling toward the sun"]
        ),
        PracticeQuestion(
            id: "ai-dog",
            author: "Ben",
            handle: "benandpepper.example",
            posted: "1d",
            caption: "Pepper meeting the ocean for the first time!!",
            imageDescription: "A golden retriever mid-leap over a wave, droplets frozen in the air. The fur looks clean and dry. Near the paws, the spray passes through the dog's legs instead of splashing around them.",
            answer: .ai,
            explanation: "Frozen droplets just mean a fast shutter. A dog leaping through a wave would be soaked, though, and water can't pass through a leg. Objects blending into each other is one of the more reliable signs left in current generators.",
            clues: ["Water passing through a solid leg", "Dry fur in the middle of a wave"]
        ),
        PracticeQuestion(
            id: "ai-historic",
            author: "History Pics Daily",
            handle: "historypicsdaily.example",
            posted: "3h",
            caption: "Rare photo: Chicago in the 1890s. They don't build them like this anymore.",
            imageDescription: "Sepia street scene with horse carriages and tall ornate buildings, covered in scratches and grain. On the right, the windows shift position from one floor to the next. The shop signs are loops that look like cursive but don't form words.",
            answer: .ai,
            explanation: "Scratches and grain are easy to add, so they prove nothing either way. Real buildings stack their windows on a grid, and shop signs were painted to be read. An account that only posts viral history shots, with no archive credit, is worth a source check too.",
            clues: ["Window grid that drifts floor to floor", "Signs that spell nothing", "No archive or photographer credit"]
        ),
        PracticeQuestion(
            id: "ai-headshot",
            author: "Northside Creative",
            handle: "northsidecreative.example",
            posted: "6h",
            caption: "New team headshots are up on the site!",
            imageDescription: "Studio portrait of a smiling woman against a gray backdrop. Her skin is very smooth. Her left earring is a gold hoop and her right is a pearl stud. Strands of hair at her shoulder fade into the backdrop.",
            answer: .ai,
            explanation: "Studio headshots are usually retouched, so smooth skin on its own isn't a sign. A retoucher doesn't swap one earring for a different one, though, and real hair has an edge even against a plain backdrop.",
            clues: ["Earrings that don't match", "Hair dissolving into the background"]
        ),
        PracticeQuestion(
            id: "ai-pastry",
            author: "Crumb & Co.",
            handle: "crumbandco.example",
            posted: "3h",
            caption: "Our new seasonal pastry is finally here 🍂",
            imageDescription: "Close-up of a glossy pastry on a marble counter, steam rising, background softly blurred. The fork beside the plate has five tines, and halfway down they merge into the handle.",
            answer: .ai,
            explanation: "Steam, shallow focus and a glossy glaze are standard food photography. A fork that melts into its own handle is the generator losing track of a simple object.",
            clues: ["Fork tines merging into the handle", "Glaze, crumbs and marble all equally polished"]
        ),
        PracticeQuestion(
            id: "ai-concert",
            author: "Midwest Gig Guide",
            handle: "midwestgigs.example",
            posted: "1d",
            caption: "Insane crowd at last night's lakefront show",
            imageDescription: "Night concert seen from behind the crowd, thousands of phones held up. Every phone screen is the same flat white glow. The stage lights are bright, but the people in the front rows are unlit.",
            answer: .ai,
            explanation: "A sea of phones is normal at concerts, but real screens show the stage at different sizes and brightness. Stage lights also wash over the front rows. Identical glowing rectangles and a dark crowd point to a generated scene.",
            clues: ["Every phone screen identical", "Front rows untouched by stage light"]
        ),
        PracticeQuestion(
            id: "ai-library",
            author: "Campus Bookworm",
            handle: "campusbookworm.example",
            posted: "6h",
            caption: "Found the coziest corner of the library 📚",
            imageDescription: "A window seat with stacked books and a cat asleep on a blanket. Titles on the nearby books are crisp; the spines on the shelf behind are covered in squiggles. Outside it's snowing hard, yet a bright sunbeam crosses the floor.",
            answer: .ai,
            explanation: "Clean titles on nearby books are easy for current generators. The shelf behind them isn't, and neither is the weather: bright direct sun doesn't come through a heavy snowstorm.",
            clues: ["Background spines that spell nothing", "Sunbeam during a snowstorm"]
        ),
    ]

    private static let edited: [PracticeQuestion] = [
        PracticeQuestion(
            id: "edit-banner",
            author: "Wildcat Watch",
            handle: "wildcatwatch.example",
            posted: "2h",
            caption: "Student council really hung this on the main quad??",
            imageDescription: "A cloth banner hung between two trees, with deep folds and wrinkles from the wind. The slogan is crisp and perfectly straight, running flat across every fold.",
            answer: .edited,
            explanation: "Printed text bends with the cloth it's on. Lettering that ignores the folds, and is sharper than the fabric around it, was added after the photo was taken.",
            clues: ["Text ignoring the fabric's folds", "Lettering sharper than its surface"]
        ),
        PracticeQuestion(
            id: "edit-market",
            author: "Celeb Spotting",
            handle: "celebspots.example",
            posted: "4h",
            caption: "She was at the farmers market today!! So down to earth",
            imageDescription: "A busy outdoor market on a sunny afternoon. Shoppers' shadows all fall to the right. The celebrity in the center has a soft shadow falling to the left and is lit more evenly than the people around her.",
            answer: .edited,
            explanation: "Everyone in one place shares one sun, so shadows point the same way. A person whose shadow and lighting disagree with the rest of the scene was cut in from another photo.",
            clues: ["Shadow pointing the other way", "Lit differently from the crowd"]
        ),
        PracticeQuestion(
            id: "edit-bleachers",
            author: "Campus Daily",
            handle: "campusdaily.example",
            posted: "1d",
            caption: "Record turnout at tonight's game.",
            imageDescription: "Bleachers packed with fans in purple, some blurred from moving. In the third row, the same group of three people in matching knit hats appears twice, a few seats apart, in the same poses.",
            answer: .edited,
            explanation: "Motion blur in a crowd is normal. The same three people in the same poses, twice, is a copy and paste to make the stands look fuller.",
            clues: ["The same people appearing twice", "Identical poses down to the hats"]
        ),
        PracticeQuestion(
            id: "edit-gym",
            author: "Fit with Jules",
            handle: "fitwithjules.example",
            posted: "8h",
            caption: "12 weeks of work. No filter, just consistency 💪",
            imageDescription: "Mirror selfie in a gym. The person's waist is very narrow. The door frame behind them is straight, except beside their waist, where it bends inward.",
            answer: .edited,
            explanation: "Phone lenses can bend a mirror selfie slightly, but evenly across the whole picture. A straight frame that curves only where it passes the body means the body was reshaped with a warp tool.",
            clues: ["Background bending only next to the body", "“No filter” on an edited photo"]
        ),
        PracticeQuestion(
            id: "edit-sunset",
            author: "Lakefront Life",
            handle: "lakefrontlife.example",
            posted: "3h",
            caption: "Sunset tonight 🌅",
            imageDescription: "A lake at sunset under a vivid orange and pink sky. The water in the foreground is pale blue with no orange in it. A faint light outline runs along the treeline where it meets the sky.",
            answer: .edited,
            explanation: "Big colorful sunsets do happen. But still water reflects the sky above it, and a light outline along the treeline is where a different sky was cut in.",
            clues: ["Water not reflecting the sky", "Outline along the treeline"]
        ),
        PracticeQuestion(
            id: "edit-moon",
            author: "Night Sky Chicago",
            handle: "nightskychi.example",
            posted: "9h",
            caption: "Supermoon over the skyline tonight!",
            imageDescription: "A huge moon behind the downtown skyline. The buildings are grainy and dark; the moon is perfectly sharp with no grain. A rooftop antenna that should cross the moon disappears behind it.",
            answer: .edited,
            explanation: "Long lenses really can make the moon look huge. A moon cleaner than everything else in the frame, sitting in front of an antenna that should block it, was pasted in.",
            clues: ["Moon cleaner than the rest of the photo", "Moon in front of the antenna"]
        ),
        PracticeQuestion(
            id: "edit-screenshot",
            author: "Daily Dunk",
            handle: "dailydunk.example",
            posted: "2h",
            caption: "Can't believe the mayor actually posted this 😂",
            imageDescription: "Screenshot of a post from the mayor's account. The post text is a little bolder than the name and timestamp above it, and the like count sits a few pixels lower than the reply count.",
            answer: .edited,
            explanation: "Screenshots of posts are the easiest thing to fake: change the words, keep the frame. Mismatched font weight and misaligned counts suggest the text was typed over. Look for the post on the account itself.",
            clues: ["Text heavier than the app's font", "Counts out of line"]
        ),
        PracticeQuestion(
            id: "edit-beach",
            author: "Shore Clean Crew",
            handle: "shorecleanup.example",
            posted: "1d",
            caption: "Before and after: we cleared the whole beach!",
            imageDescription: "The “after” photo: an empty beach with smooth sand and no footprints anywhere, even right beside the volunteers' bags. Near the waterline, the same ripple shape appears three times.",
            answer: .edited,
            explanation: "A clean beach after a cleanup is believable. No footprints next to the bags of the people who did it, and one patch of ripples repeated, show a removal tool filling in where things used to be.",
            clues: ["No footprints where people stood", "One patch of sand repeated"]
        ),
    ]

    private static let real: [PracticeQuestion] = [
        PracticeQuestion(
            id: "real-fire",
            author: "Dana Ruiz",
            handle: "danaruiz.example",
            posted: "40m",
            caption: "Fire crews on Church St right now. Road closed between Chicago Ave and Hinman.",
            imageDescription: "Grainy night photo of a fire truck, with red streaks from its flashing lights. Slightly out of focus.",
            context: "Reply from @danaruiz.example: two more photos from the other side of the street.",
            answer: .real,
            explanation: "Grain, light streaks and soft focus are what phone cameras do at night. More angles of the same moment, from someone naming exact streets you can check, point to a real photo.",
            clues: ["Night-photo flaws that fit the conditions", "Several angles from the same person"]
        ),
        PracticeQuestion(
            id: "real-storm",
            author: "Ana K.",
            handle: "anak.example",
            posted: "2h",
            caption: "The lake is wild today",
            imageDescription: "Huge waves crashing over a lakefront path under a gray sky. Ice coats the railings and benches where the spray lands. A water spot on the lens blurs one corner.",
            answer: .real,
            explanation: "It's dramatic, but every detail agrees: ice exactly where the spray reaches, the same flat gray light everywhere, and a drop on the lens. Several other people posted the same storm that afternoon.",
            clues: ["Details that agree with each other", "Other posts of the same event"]
        ),
        PracticeQuestion(
            id: "real-kitchen",
            author: "Sam Okafor",
            handle: "samokafor.example",
            posted: "1d",
            caption: "Dinner party aftermath. Worth it.",
            imageDescription: "A cluttered kitchen counter under warm overhead light: stacked plates, wine glasses, a sticky note reading “oven still on??”, and the photographer's phone reflected in the toaster.",
            answer: .real,
            explanation: "Readable handwriting, everyday clutter and the photographer reflected in a shiny surface are hard for a generator to get right all at once. Messy and specific usually means real.",
            clues: ["Small text you can actually read", "The photographer's reflection"]
        ),
        PracticeQuestion(
            id: "real-rainbow",
            author: "Mia Chen",
            handle: "miachen.example",
            posted: "5h",
            caption: "Took this through the bus window, can't believe it came out",
            imageDescription: "A double rainbow over a parking lot. A faint reflection of bus seats lies across the whole picture. The outer rainbow's colors run in the opposite order to the inner one.",
            answer: .real,
            explanation: "It looks almost too good, but a second rainbow with reversed colors is real optics, and a seat reflection is exactly what shooting through glass looks like. Unusual isn't the same as fake.",
            clues: ["Reversed outer rainbow is real physics", "Glass reflection fits the story"]
        ),
        PracticeQuestion(
            id: "real-dog",
            author: "Jordan Lee",
            handle: "jordanlee.example",
            posted: "3h",
            caption: "My dog would not sit still for this photo",
            imageDescription: "A dog's face mid-shake, ears flying, the snout blurred with motion. Behind it, a messy living room: laundry on the couch, a TV remote on the floor.",
            answer: .real,
            explanation: "Blur only on the parts that move, in an untidy and specific room, is what phone photos look like. Generated pictures lean toward clean rooms and crisp subjects.",
            clues: ["Blur only where things move", "Ordinary, specific mess"]
        ),
        PracticeQuestion(
            id: "real-shelf-cloud",
            author: "Prairie Weather Notes",
            handle: "prairieweather.example",
            posted: "4h",
            caption: "Shelf cloud rolling over Naperville right now",
            imageDescription: "A huge layered cloud shaped like a flying saucer over a strip-mall parking lot. Cars have their headlights on in the daytime, and the wet pavement reflects the cloud's underside.",
            answer: .real,
            explanation: "Shelf clouds look unreal but are common ahead of summer storms. The reflection in the wet pavement matches the cloud, and headlights on in the daytime fit the sudden dark.",
            clues: ["Reflection matching the sky", "Details that fit a sudden storm"]
        ),
        PracticeQuestion(
            id: "real-sign",
            author: "Pat's Diner",
            handle: "patsdiner.example",
            posted: "1d",
            caption: "Our new sign guy tried his best 😅",
            imageDescription: "A hand-painted diner sign reading “OPEN 24 HOURS EXCPET TUESDAY”. Brush strokes show in every letter, paint has dripped under the T, and a ladder leans against the wall below.",
            answer: .real,
            explanation: "A misspelling alone doesn't mean AI. These letters are consistent and painted, with drips and brush marks, and the ladder and caption explain the mistake. Generated text fails differently, with shapes that aren't letters.",
            clues: ["A human misspelling, not invented letters", "Brush strokes and drips"]
        ),
    ]

    private static let misleading: [PracticeQuestion] = [
        PracticeQuestion(
            id: "mis-flood",
            author: "Morning Brief",
            handle: "morningbrief.example",
            posted: "30m",
            caption: "BREAKING: flooding downtown right now",
            imageDescription: "Cars underwater up to their windows on a flooded city street. In the corner, a watermark shows another photographer's name and the year 2019.",
            answer: .misleading,
            explanation: "Nothing in the picture is edited or generated. It's an old photo with a new caption, the most common kind of misleading post, and no detector can catch it. Check the date and who took it.",
            clues: ["A real photo with the wrong date", "Credit pointing to someone else"]
        ),
        PracticeQuestion(
            id: "mis-protest",
            author: "Breaking Alerts Now",
            handle: "breakingalertsnow.example",
            posted: "20m",
            caption: "HAPPENING NOW: massive protest outside City Hall",
            imageDescription: "A large crowd with signs outside a domed government building. The trees are bare and people wear heavy coats. Several signs urge a yes vote on a 2020 ballot measure.",
            answer: .misleading,
            explanation: "Nothing in the picture is edited or generated. The signs are about a vote from years ago, so the photo is real and the “happening now” story is false.",
            clues: ["Signs about an old vote", "Real photo, new caption"]
        ),
        PracticeQuestion(
            id: "mis-wrong-city",
            author: "World News Clips",
            handle: "worldnewsclips.example",
            posted: "2h",
            caption: "Chicago tonight after the storm 😳",
            imageDescription: "A flooded street of low houses with palm trees bending in the wind. A street sign reads “Calle 8”.",
            answer: .misleading,
            explanation: "The photo is real and untouched, but palm trees and a Calle 8 sign don't belong in Chicago. A real photo from another city, given a local caption, is still a false story.",
            clues: ["Scenery that doesn't fit the place", "A street sign from somewhere else"]
        ),
        PracticeQuestion(
            id: "mis-early",
            author: "Campus Rumor Mill",
            handle: "campusrumors.example",
            posted: "5h",
            caption: "Look how empty the president's speech was lol",
            imageDescription: "Rows of mostly empty folding chairs in a hall, taken from the back corner. A wall clock reads 5:40, and a program on one chair says the speech starts at 6:30.",
            answer: .misleading,
            explanation: "The photo is real, but it was taken almost an hour before the event. A real picture used to suggest something that didn't happen is misleading, not fake.",
            clues: ["Clock and program show it's early", "Caption claims more than the photo shows"]
        ),
        PracticeQuestion(
            id: "mis-called-ai",
            author: "Truth Seeker",
            handle: "truthseeker.example",
            posted: "1d",
            caption: "This viral rescue photo is obviously AI, wake up",
            imageDescription: "A firefighter carrying a kitten out of a smoky doorway.",
            context: "Quoted by a local news site, with two more angles of the same moment credited to its staff photographer.",
            answer: .misleading,
            explanation: "The photo is real; the false part is the caption calling it AI. Calling real photos fake misleads people too, and other angles from a named photographer settle it.",
            clues: ["Same moment from other angles", "The caption is the false part"]
        ),
        PracticeQuestion(
            id: "mis-stock",
            author: "Local Heroes Daily",
            handle: "localheroesdaily.example",
            posted: "3h",
            caption: "This nurse just worked 30 hours straight to save our town 🙏",
            imageDescription: "A smiling nurse in spotless scrubs against a soft blue backdrop, lit evenly from the front, face perfectly centered.",
            answer: .misleading,
            explanation: "It's a real stock photo, the kind sold for ads, not a nurse from your town. Studio light and a plain backdrop don't fit a 30-hour shift. A reverse image search finds it on stock sites.",
            clues: ["Stock-photo lighting and backdrop", "A story the picture can't back up"]
        ),
        PracticeQuestion(
            id: "mis-coach",
            author: "Sports Takes",
            handle: "sportstakes.example",
            posted: "30m",
            caption: "Coach just announced he's leaving!!",
            imageDescription: "A coach at a press-conference podium in front of a team banner. The banner carries a sponsor logo the team dropped years ago, and the coach looks noticeably younger than this season.",
            answer: .misleading,
            explanation: "It's a real press conference, from years ago; the old sponsor logo dates it. Nothing in the picture shows the announcement the caption claims.",
            clues: ["Old branding dates the photo", "News the photo doesn't show"]
        ),
    ]
}
