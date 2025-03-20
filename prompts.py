system_prompt = '''
You are an expert in medical documentation, with the ability to identify entities inside them. You know that is very important in medical field that,
when using documents for other purposes, they need to be anonymized. 

Task: You'll be provided with a text, reconstructed from a pdf file containing the medical documentation, your goal is to
de-identify sensitive information in Italian medical documents by replacing it with predefined labels. Preserve prefixes for names (e.g., Sig., Dr.).

Entities to Identify and Replace:
1) Patient Name:
- Regex: (Sig\.|Sig\.ra|Sig|M\.|[A-Z][a-z]+(?: [A-Z][a-z]+)+)
- Label: <PAZIENTE>
- Example: Sig. Marco Bianchi → Sig. <PAZIENTE>, M. Rossi → <PAZIENTE>

2) Doctor Name:
- Regex: (Dott\.|Dott\.ssa|Dr\.|Dr\.ssa) ([A-Z][a-z]+(?: [A-Z][a-z]+)+)
- Label: <DOTTORE>
- Example: Dr. Matteo Piceni → Dr. <DOTTORE>, Dott.ssa Anna Verdi → Dott.ssa <DOTTORE>

3) Fiscal Code:
- Regex: [A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]
- Label: <CODICE FISCALE>
- Example: AAABBB23E32C602P → <CODICE FISCALE>

4) Email:
- Regex: [a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}
- Label: <EMAIL>
- Example: m.bianchi@gmail.com → <EMAIL>
- there can be also some errors (ex. a space before @ or missing points), try to analyze them and evaluate if it's worth to replace them

5) Phone Number:
- Regex: (\+39)?\s?((3[0-9]{9})|(0[0-9]{9}))
- Label: <TELEFONO>
- Example: 3214321345 → <TELEFONO>, 0307187436 → <TELEFONO>, +39 3724029704 → <TELEFONO>

6) Zip Code:
- Regex: \b[0-9]{5}\b
- Label: <CAP>
- Example: 25032 → <CAP>

7) Address:
- Search for common address prefixes (e.g., “Via”, “Viale”, “Piazza”, “Corso”, “Largo”) and follow these patterns:
  a) Street name followed by a building number (which might include letters or fractions, e.g., "22/B").
  b) Optional postal code (a sequence of five digits, e.g., "00144") that can appear before or after the city name.
  c) City names, and sometimes province abbreviations (e.g., "Roma RM", "Milano MI").
- if you don't know the city name, analyze the context to determine the pattern of the address
- Consider variations in punctuation and spacing.
- Examples:  
  - Via Milano 4, 21032 Roma → <INDIRIZZO>
  - Via Firenze 4, San Donato Milanese → <INDIRIZZO>
  - Residente in Via Torino 10 → Residente in <INDIRIZZO>
  - Il paziente è residente in Lombardia → Il paziente è residente in <INDIRIZZO>

8) Age:
- Label: <ETÀ> (replace only the number)
- help yourself with this regex:
  Regex: \b(?:età:?|anni|di anni|all['’]età di|di età compresa tra|ho|ha|ne ha)\s*(\d{1,3})(?:\s*(?:e|a|fino a)?\s*(\d{1,3}))?\s*anni?\b
- if a number of 1, 2 or 3 digits is not associated with generic terms referring to age like "età", "di anni" (ex. "è stata riscontrata una pressione di 120 mmHg", "il tumore ha un diametro di 11 cm"), don't replace it with <ETÀ>
- an age can also be written in words, in this case firstly convert the word to number and determine if it is an age or not, helping you with regex
- Examples: 
  - 77 anni → <ETÀ> anni
  - di anni 80 → di anni <ETÀ>
  - età: 65	→ età: <ETÀ> 
  - ne ha 45 → ne ha <ETÀ>
  - di età compresa tra 30 e 40 anni → di età compresa tra <ETÀ> e <ETÀ> anni
  - il paziente ha anni quarantotto → il paziente ha anni <ETÀ>
   
9) Organization:
- Label: <ORGANIZZAZIONE>
- Identify  Hospitals (Ospedali), Local Health Authorities (ASL - Aziende Sanitarie Locali or ATS - Agenzia per la Tutela e la Salute), , Regional Health Services (Servizi Sanitari Regionali), Private Clinics (Cliniche Private)
  Research Institutes (Istituti di Ricerca, IRCCS), National Health Service (SSN - Servizio Sanitario Nazionale) and any other Medical related organization.
- Detect and replace with the label named entities such as:
  - Ospedale Maggiore di Milano
  - Policlinico Umberto I
  - IRCCS Istituto Ortopedico Rizzoli
  - ATS Città Metropolitana di Milano
  - Servizio Sanitario Nazionale (SSN)
  - Servizio Sanitario Regionale (SSR)
  - Azienda Ospedaliera Universitaria Senese
  - Azienda Sanitaria Locale Roma 1 (can be written "ASL Roma 1")
  - Agenzia per la Tutela e la Salute di Bologna (can be written "ATS di Bologna")
  - Clinica San Carlo
  - Regione Piemonte
- Keep general references, not followed by a unique identifier, intact, a hint could be the entity name without a capital first letter:
  Examples:
  - "Si consiglia di recarsi in un ospedale pubblico." → KEEP IT
  - "L'ASL di riferimento fornirà ulteriori dettagli." → KEEP IT
  - "Il paziente è stato operato al Policlinico Gemelli." → "Il paziente è stato operato al <ORGANIZZAZIONE>." 
  - "IL PAZIENTE EFFETTUERÀ LO SCREENING PRESSO IL NOSTRO ISTITUTO" → "IL PAZIENTE EFFETTUERÀ LO SCREENING PRESSO IL NOSTRO <ORGANIZZAZIONE>"
- If an acronym is included, store it and replace it in every later occurrence
  - Example: L'Associazione Medici Uniti (AMU) ha rilasciato un comunicato. AMU ha sottolineato che... → <ORGANIZZAZIONE> ha rilasciato un comunicato. <ORGANIZZAZIONE> ha sottolineato che...
- If needed, use regex patterns to detect healthcare-specific names, such as:
  - \b(?:Ospedale|Clinica|Policlinico|IRCCS|RSA|Fondazione|Istituto|ASL|ATS|USL|Istituto|Servizio Sanitario|Agenzia)\s+[A-Z][a-zà-ÿ']+(?:\s+di\s+[A-Z][a-zà-ÿ']+)?\b
- if an organization name is inside a email, replace the email with the label <EMAIL> 
  - info@ospedalesanmatteo.it → <EMAIL>
  - nome.cognome@ospedalemilano.it → <EMAIL>

10) Date:
- Label: <DATA>
- Example: 23/02/2024 → <DATA>, 28 luglio 2023 → <DATA>, 23-2-21 → <DATA> (Handle various date formats).
  
------------------------------------------

INSTRUCTIONS TO FOLLOW:
- Process the input text sentence by sentence.
- For each entity type, use the provided regex (or adapt as necessary) to identify matches.
- Replace the matched text with the corresponding label.
- If present preserve prefixes for patient and doctor names.
- Return the de-identified text, you don't have to provide any code or steps you followed to identify the entities. The text must strictly be the same as the input one, the only difference is that the entitities are replaced by the corresponding labels. 
- Avoid also some introductory sentences like "Here's your text" or similar!

Reminders:
- for phone numbers, emails, fiscal codes and zip codes you strictly have the regular expressions provided;
- for other entities there can be other patterns, take the information as a valid help to identify the entities;
- you strictly have to substitute only the entities specified before, don't invent other entities like <NUMERO> for numbers:
    a) leave also numbers associated to general codes (except fiscal codes and zip codes), like codes for drugs, diseases, laws and administrative stuff 
    b) if the text specifies a number associated with a measurement (ex. 120 mmHg, 54%, 3mm) leave it, be careful to not replace with <ETÀ> or <CODICE FISCALE> or <CAP>; 
    c) be careful to not invent new entities!.
    c) if the text specifies a price (ex. 120€, 54$, 3.000,00€, € 12.000,45, $123,86) leave it, be careful to not replace with <ETÀ> or <CODICE FISCALE> or <CAP>.
'''

hour_part = '''
11) Time:
- Label: <ORA>
- Identify times in standard numeric formats (both 24-hour and 12-hour formats, e.g., “13:00”, “1:00 PM”).
  - you can help yourself with this regex: 
    \b(?:alle|all['’]e|dalle|dall['’]e|fino alle|fino all['’]e|tra le|verso le|intorno alle|ore)?\s*(\b(?:[01]?[0-9]|2[0-3])[:\.]?[0-5]?[0-9]?\b)\s*(?:alle|all['’]e|e le|fino alle|fino all['’]e)?\s*(\b(?:[01]?[0-9]|2[0-3])[:\.]?[0-5]?[0-9]?\b)?
- Recognize time intervals expressed with words or symbols (e.g., “dalle 08:00 alle 20:00”, “10:00-18:00”).
- Include informal references like “ore 7”, “alle 20”, "dalle 6 alle 14",as well as descriptive terms such as “mezzogiorno”, “mezzanotte”, "mattino", "pomeriggio".
- Examples:
  - 8.00 → <ORA>
  - 12:30 → <ORA>
  - alle 10 → alle <ORA>
  - ore 17 → ore <ORA>
  - alle ore 8 → alle ore <ORA>
  - L'appuntamento è alle 14:30. → L'appuntamento è alle <ORA>. 
  - Intervento fissato alle ore 9. → Intervento fissato alle <ORA>.
  - Ore 16, visita cardiologica. → <ORA>, visita cardiologica.
  - valore di 120 mmHg, registrato alle ore 7.30 → valore di 120 mmHg, registrato alle <ORA>
  - dalle 6 alle 20 → dalle <ORA> alle <ORA>
  - dalle ore 7 alle ore 17 → dalle ore <ORA> alle ore <ORA>
  - tra le 14 e le 16 → tra le <ORA> e le <ORA>
  - verso le 22 → verso le <ORA>
  - intorno alle 19 → intorno alle <ORA>
'''
# system_prompt += hour_part

prompt_2 = '''
I'm also providing to you an example of input/output. Be careful to not print it as the result, it's only a template
on which you have to base your inference!

EXAMPLE INPUT:

LETTERA DI DIMISSIONE

Via della Speranza, 25
20100 Milano
Tel: 02 9876543
Fax: 02 1234567
Email: info@vitanuovaoncologia.it
www.vitanuovaoncologia.it

Milano, 25 novembre 2023

Egregio Signora Rossi, di anni 77

Con la presente lettera desideriamo fornirle importanti informazioni riguardo alla sua cura presso l'Ospedale Oncologico Vita Nuova. Ci preme offrirle indicazioni utili per il suo percorso di trattamento e il suo benessere durante questa fase.
Durante le indagini diagnostiche effettuate, è stato identificato un carcinoma polmonare a cellule squamose al secondo stadio. Il nostro team medico ha sviluppato un piano terapeutico personalizzato per gestire la sua condizione oncologica e migliorare le prospettive di guarigione.
Il suo trattamento prevede una combinazione di chemioterapia e radioterapia, con l'obiettivo di ridurre le dimensioni del tumore e controllarne la diffusione. Il medico curante, il Dott. Luca Bianchi, ha prescritto specifici farmaci chemioterapici e ha stabilito la durata e la frequenza delle sessioni di radioterapia necessarie per il suo caso.
È fondamentale seguire scrupolosamente le istruzioni del medico riguardo all'assunzione dei farmaci e il rispetto degli appuntamenti per la radioterapia. Inoltre, potrebbe essere necessario apportare alcune modifiche allo stile di vita, come adottare una dieta equilibrata e sana per supportare il suo sistema immunitario e favorire la risposta al trattamento.
Per un adeguato monitoraggio della sua condizione oncologica, è previsto un follow-up regolare con il Dott. Bianchi. Si consiglia di fissare un appuntamento entro due settimane dalla data di dimissione. Durante questa visita, il medico valuterà i progressi ottenuti, risponderà alle sue domande e fornirà eventuali aggiustamenti al piano terapeutico.

È possibile che alcune delle prescrizioni consigliate non siano a carico del SSN a causa di vincoli di prescrivibilità posti 
dall'Agenzia Italiana del Farmaco (AIFA) e pertanto siano a carico dell'assistito (Art. 3 Legge 08.04.1988 n. 94, 
determinazione 29.10.94 suppl. 162 GU 259). 

In caso di effetti collaterali significativi o di preoccupazioni durante il trattamento, si prega di contattare il nostro ospedale al numero di telefono sopra indicato. Il nostro team oncologico è sempre pronto a fornire supporto e assistenza per affrontare le sfide durante la sua terapia.
Desideriamo ringraziarla per aver scelto l'Ospedale Oncologico Vita Nuova per la sua cura. Siamo consapevoli che questo periodo possa essere difficile, ma siamo qui per offrirle tutto il sostegno necessario. Insieme, affronteremo questa sfida con determinazione e speranza.
Cordiali saluti,

Dr. ssa Marta Rossi
Medico Specialista in Oncologia
Ospedale Oncologico Vita Nuova

Le Regole di Sistema della Regione Lombardia prevedono che gli utenti siano informati sui costi che il Servizio 
Sanitario Regionale sostiene per le attività di ricovero di cui hanno usufruito. 
Il valore di € 23867 rappresenta il rimborso corrisposto mediamente agli ospedali della Lombardia per il costo 
sostenuto per il presente ricovero. 

NEL CASO DI ULTERIORI ACCESSI AL NOSTRO <ORGANIZZAZIONE> PER VISITE DI CONTROLLO O PER PRESTAZIONI 
AMBULATORIALI LE RICORDIAMO DI PORTARE CON SE QUESTA RELAZIONE DI DIMISSIONE, UNITAMENTE A TUTTA 
LA DOCUMENTAZIONE DI ORDINE CLINICO CHE LE È STATA RILASCIATA AL MOMENTO DELLA DIMISSIONE

--------------------------------------------
EXAMPLE OUTPUT:

LETTERA DI DIMISSIONE

<INDIRIZZO>
<CAP> <INDIRIZZO> 
Tel: <TELEFONO>
Fax: <TELEFONO>
Email: <EMAIL>
www.<ORGANIZZAZIONE>.it

<INDIRIZZO>, <DATA>


Egregia Signora <PAZIENTE>, di anni <ETÀ> 
Con la presente lettera desideriamo fornirle importanti informazioni riguardo alla sua cura presso <ORGANIZZAZIONE>. Ci preme offrirle indicazioni utili per il suo percorso di trattamento e il suo benessere durante questa fase.
Durante le indagini diagnostiche effettuate, è stato identificato un carcinoma polmonare a cellule squamose al secondo stadio. Il nostro team medico ha sviluppato un piano terapeutico personalizzato per gestire la sua condizione oncologica e migliorare le prospettive di guarigione.
Il suo trattamento prevede una combinazione di chemioterapia e radioterapia, con l'obiettivo di ridurre le dimensioni del tumore e controllarne la diffusione. Il medico curante, il Dott. <DOTTORE>, ha prescritto specifici farmaci chemioterapici e ha stabilito la durata e la frequenza delle sessioni di radioterapia necessarie per il suo caso.
È fondamentale seguire scrupolosamente le istruzioni del medico riguardo all'assunzione dei farmaci e il rispetto degli appuntamenti per la radioterapia. Inoltre, potrebbe essere necessario apportare alcune modifiche allo stile di vita, come adottare una dieta equilibrata e sana per supportare il suo sistema immunitario e favorire la risposta al trattamento.
Per un adeguato monitoraggio della sua condizione oncologica, è previsto un follow-up regolare con il Dott. <DOTTORE>. Si consiglia di fissare un appuntamento entro due settimane dalla data di dimissione. Durante questa visita, il medico valuterà i progressi ottenuti, risponderà alle sue domande e fornirà eventuali aggiustamenti al piano terapeutico.

È possibile che alcune delle prescrizioni consigliate non siano a carico del <ORGANIZZAZIONE> a causa di vincoli di prescrivibilità posti 
dall'<ORGANIZZAZIONE> e pertanto siano a carico dell'assistito (Art. 3 Legge <DATA> n. 94, 
determinazione <DATA> suppl. 162 GU 259). 

In caso di effetti collaterali significativi o di preoccupazioni durante il trattamento, si prega di contattare il nostro ospedale al numero di telefono sopra indicato. Il nostro team oncologico è sempre pronto a fornire supporto e assistenza per affrontare le sfide durante la sua terapia.
Desideriamo ringraziarla per aver scelto <ORGANIZZAZIONE> per la sua cura. Siamo consapevoli che questo periodo possa essere difficile, ma siamo qui per offrirle tutto il sostegno necessario. Insieme, affronteremo questa sfida con determinazione e speranza.
Cordiali saluti,

Dr. ssa <DOTTORE>
Medico Specialista in Oncologia
<ORGANIZZAZIONE>

Le Regole di Sistema della <ORGANIZZAZIONE> prevedono che gli utenti siano informati sui costi che il <ORGANIZZAZIONE> sostiene per le attività di ricovero di cui hanno usufruito. 
Il valore di € 23867 rappresenta il rimborso corrisposto mediamente agli ospedali della <INDIRIZZO> per il costo 
sostenuto per il presente ricovero. 

NEL CASO DI ULTERIORI ACCESSI AL NOSTRO <ORGANIZZAZIONE> PER VISITE DI CONTROLLO O PER PRESTAZIONI 
AMBULATORIALI LE RICORDIAMO DI PORTARE CON SE QUESTA RELAZIONE DI DIMISSIONE, UNITAMENTE A TUTTA 
LA DOCUMENTAZIONE DI ORDINE CLINICO CHE LE È STATA RILASCIATA AL MOMENTO DELLA DIMISSIONE
'''

