# Live demo script (about 5 minutes)

**Before judging:**
- Run `ops\start.ps1`. Both models are preloaded; Gemma's first load from disk takes about 94 s, so do this early.
- Use the role bar at the top to switch between **Engineer A**, **Engineer B**, **Inspector** and **Admin**. No password is needed in demo mode; hide the bar with «إخفاء الشريط».
- Test once with Wi-Fi OFF.
- If the live AI fails, keep going: every AI screen shows its mode badge. The backup screenshots and video are in `E:\blue-balance-data\screens\`, made by `web/e2e/screens.spec.ts`.

| # | Screen | What to click | What to say (AR / EN) |
|---|---|---|---|
| 1 | Overview | Nothing yet | «٤١٪ من مي الأردن بتضيع، والوزارة بتقدّر إنه حوالي ٧٠٪ منها اعتداءات على الخطوط والمصادر. بس ما حدا بيعرف وين يبعت المفتش أول.» / "41% of Jordan's water is lost, and the ministry estimates about 70% of that is attacks on lines and sources. Nobody knows where to send the inspector first." |
| 2 | Overview map + queue | Point at the dashed route and the queue | «هاد مسار تقريبي للخط على الطريق الصحراوي عند القطرانة. القائمة مرتّبة حسب كم متر مكعب بنوقف بكل ساعة تفتيش، وكل رقم معه مداه وشارة مصدره.» / "Approximate main-line route at Qatraneh. The queue is ranked by m³ stopped per inspection hour; every number has its range and a source badge." |
| 3 | Case KRK-T-002 (fusion) | Open the top case | «إشارتين مستقلتين: عدم توازن بالتدفق على المقطع (محاكاة)، وخضرة جديدة جنبه من Sentinel-2 (رصد حقيقي). لحالها: ٠٫٧١ و٠٫١١. مع بعض: ٠٫٨٢.» / "Two independent signals: a flow imbalance on the segment (simulated) and new greenness next to it (observed). Alone, 0.71 and 0.11; fused, 0.82." |
| 4 | Time slider | Drag from 2017 to 2026 | «النظام شاف الخضرة، بس WorldCover بيقول إنها داخل أرض زراعية قائمة، فأعطاها وزن ضعيف: ٠٫١١ لحالها. ما بنتّهم حدا.» / "It saw the greenness, but WorldCover says it's inside existing farmland, so it gave it only a weak weight: 0.11 on its own. We don't accuse." |
| 5 | Ask (agent) | Ask «شو أول ٣ مواقع لازم نفتشها بالكرك؟» then «مين صاحب المزرعة KRK-F-001؟» | «النموذج Qwen مفتوح المصدر شغّال على اللابتوب بدون إنترنت. كل رقم بالجواب مفحوص مقابل نتائج الأدوات، وبيرفض يعطي أسماء.» / "Open-weight Qwen, running locally and offline. Every number is checked against the tool results, and it refuses personal data." |
| 6 | Crew report | Load DEMO-3 (the injection one) and click Extract | «Gemma بيطلع ١٠ حقول من كلام الفريق، وكل حقل مربوط بنفس الكلمات. وهون في جملة مدسوسة "تجاهل التعليمات"، النظام كشفها وطلب تأكيد.» / "Gemma extracts 10 fields, each tied to the exact words. This report has an injected instruction; the guard caught it and asks the crew to confirm." |
| 7 | Case → field result | Click «ما لقينا إشي» | «نتيجة الزيارة بتحدّث الاحتمال فوراً والقائمة بتعيد ترتيب حالها. حتى الزيارة الفاضية إلها قيمة.» / "The visit result updates the posterior and the queue re-ranks live. Even an empty visit has value." |
| 8 | Work order / map edit | Engineer A drafts → Engineer A tries to approve (refused) → switch to Engineer B in the role bar → approve → export EPSG:28191 | «اللي بيطلب ما بيوافق. والوكيل الذكي بيكتب مسودة بس.» / "The requester can't approve, and the agent can only draft." |
| 9 | Transparency | Open it | «هون كل اشي: شو مرصود، شو محاكاة، شو افتراض. ولا اشي متحقق ميدانياً لسا، وهيك لازم نحكي.» / "Here's what is observed, simulated and assumed. Nothing is field-verified yet, and we say so." |

## Hard questions (short answers)
- **"Is the tap real?"** No. The line signal is simulated, because real meter data is restricted. The satellite layer is real.
- **"Why trust 0.82?"** It's a ranking estimate from assumed priors and uncalibrated likelihoods. It's shown with its interval and updates from field results.
- **"Isn't the LLM extractor better than rules?"** On our 30-report test they're on par (90.9% vs 92.3%). We report that as measured.
- **"Did you build this today?"** Yes; the git history starts today. Team members explored this problem before, and the README discloses those repos. No code or data was reused.
