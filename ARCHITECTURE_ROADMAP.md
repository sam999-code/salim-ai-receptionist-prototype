# Roadmap: من نموذج محادثة إلى مساعد شركة

هذه خطة تعلّم وتنفيذ؛ العناصر التالية **لم تُبنَ بعد** ما لم يُذكر خلاف ذلك. البداية الحالية هي `Webhook` يتحقق من الطلبات ويعرض `Draft reply (not sent)`، مع تجربة محلية لـ Claude واختبارات Python. لا يوجد إرسال آلي، قاعدة معرفة للشركة، حجز فعلي، نظام هاتف، أو اتصال بـ POS.

## كيف سيعمل النظام

```text
WhatsApp / phone event
  → verified channel adapter
  → conversation state + identity/authorization check
  → intent and detail extraction
  → approved company knowledge lookup
  → decision: answer, ask one useful question, hand off, or propose a tool action
  → tool-policy validation and (when needed) human/customer confirmation
  → business system (calendar / CRM / reservation / POS)
  → verified outcome + concise customer update
```

## ترتيب البناء في الدروس القادمة

1. **حدد سياسة العمل ومصدر الحقيقة.** اجمع الخدمات والأسعار وساعات العمل والأسئلة الشائعة وحدود ما يُسمح للمساعد بوعد العميل به. كل معلومة لها مالك وتاريخ مراجعة. عند غياب معلومة مؤكدة، يسأل أو يحيل لسليم.
2. **صمّم `Conversation state` و`Contact record`.** خزّن القناة ومعرّف المحادثة والنية والتفاصيل المؤكدة والحالة (`collecting`, `awaiting_confirmation`, `handoff`, `closed`) في قاعدة بيانات. رقم WhatsApp يحدد المحادثة، لكنه لا يثبت هوية الشخص القانونية. افصل البيانات بين العملاء، وحدد مدة احتفاظ وحذف.
3. **أضف معرفة الشركة.** ابدأ بملفات منظمة صغيرة أو جداول للأسعار والخدمات بدل قاعدة متجهات فورًا. أضف `Retrieval` فقط عندما تكبر الوثائق ويحتاج الرد إلى مقاطع موثقة. لا تسمح لنص عميل أو صفحة خارجية بتعديل سياسة الشركة.
4. **أضف أدوات محدودة.** مثل `check_availability` للقراءة، ثم `create_reservation` أو `create_lead` بمعاملات محددة وموثقة. التطبيق، لا النموذج، يتحقق من الصلاحية وصحة التاريخ والوقت وتكرار الطلب ونتيجة النظام. طلب الحجز ليس تأكيدًا؛ أرسل `confirmed` فقط بعد نجاح أداة الحجز.
5. **أضف حدود أمان واضحة.** تعامل مع رسالة العميل ونتائج البحث والوثائق الخارجية كنصوص غير موثوقة. امنع الوصول العام للملفات والشبكة والأسرار، اسمح بالأدوات اللازمة فقط، وتحقق من معاملات كل استدعاء خارج النموذج. تتطلب الإجراءات المؤثرة مراجعة أو تأكيدًا مناسبًا. لا تعتمد على Prompt وحده لمنع `Prompt Injection`.
6. **اختبر المحادثة والعمل.** حالات تشمل تغيير الرأي، الغموض، طلب الطعام خارج نطاق الشركة، سؤال السعر، تكرار الرسائل، فشل الأدوات، وتسرب التعليمات. قِس جودة الرد، نجاح المهمة، والأسئلة المتكررة. لدينا 25 اختبار Python محليًا وملف `Promptfoo`؛ تقييم Anthropic الحي لم يكتمل بعد.
7. **أضف المراقبة ثم النشر المحدود.** سجّل معرفات الأحداث وقرارات الأدوات والأخطاء من دون مفاتيح أو بيانات شخصية غير لازمة. جرّب على حسابات اختبار، ثم مراجعة بشرية للردود، ثم إرسال محدود. المكالمات الهاتفية الصادرة والواردة مرحلة مستقلة تحتاج مزود هاتف، موافقات، وقواعد تشغيل خاصة.

## مواد موثوقة للمتابعة

- [Anthropic — Building effective agents](https://www.anthropic.com/research/building-effective-agents): متى تكفي سلسلة خطوات بسيطة ومتى نحتاج agent يتخذ قرارات ويستخدم أدوات.
- [Anthropic — Tool use with Claude](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview): تعريف الأدوات وعودة `tool_use` إلى التطبيق ليُنفّذها ويتحقق منها.
- [OWASP — LLM Prompt Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html): حدود الثقة، فحص الصلاحيات عند الأدوات، وتقليل الامتيازات.
- [Langfuse — Sessions](https://langfuse.com/docs/observability/features/sessions): تتبع المحادثة عبر أحداث متعددة لمراجعة السلوك؛ نضيفه عندما نصل إلى تشغيل فعلي.
- [Meta — WhatsApp Developer Hub](https://whatsappbusiness.com/developers/developer-hub/): نقطة البداية الرسمية لـ `Cloud API` و`Webhooks` ومتطلبات التشغيل.
- [فيديو: How We Build Effective Agents](https://ai.engineer/talks/D7_ipDqhtwk-effective-ai-agents): عرض قصير من مهندس Anthropic عن اختيار المهام المناسبة للـ agent وتصميم أدواته.

**أول درس تالٍ:** سنحدد شركة واحدة وخدمتين فقط، ونكتب بياناتها المعتمدة وأمثلة أسئلة العملاء. ثم نبني `Conversation state` محليًا ونقارن النتائج بأمثلة المحادثات التي فشلت اليوم.
