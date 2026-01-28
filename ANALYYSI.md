### 1. Mitä tekoäly teki hyvin?
Tekoäly toimi hyvin mekaanisena koodintuottajana. Se nopeutti kehitysprosessia valtavasti automatisoimalla koodin kirjoituksen. Siitä (lukuisissa eri instansseissa) oli myös apua iteratiivisessa debuggauksessa. Spesifioin promptissani sen käyttämään ohjelmistokehityksen parhaita periaatteita, ja luultavasti tämän vuoksi se luonnosteli projektin perustan sangen modulaarisesti ja siististi. 

Erikseen mainitsematta se valitsi UUID-formaatin varausten identifioinnille; olisin valinnut sen itse myös. Vaikka näin yksinkertaisessa projektissa saattaisi olla selkeämpää käyttää yksinkertaista kokonaislukujatkumoa, mielestäni on järkevää valmistautua jo varhaisessa vaiheessa järjestelmän skaalautuvuuteen. UUID estää tunnisteiden ennustettavuuden ja helpottaa tietojen yhdistämistä eri lähteistä ilman päällekkäisyyksiä, mikä tekee arkkitehtuurista huomattavasti vikasietoisemman. Näin vältetään myös mahdolliset ID-seurantaan liittyvät konfliktit.

### 2. Mitä tekoäly teki huonosti?
Ensimmäisellä promptilla agentti tuotti "luurangon" projektille: kehitysserveri käynnistyi, rajapinnan dokumentaatio oli käytettävissä SwaggerUI:n kautta, ja sen kautta pystyi tekemään API-kutsuja. Jokainen kutsu kuitenkin aiheutti käsittelemättömän HTTP-virheen (500), koska muistinvarainen tietokanta ei initialisoitunut kunnolla. Pyydettyäni samaista agenttia tutkimaan ja korjaamaan asian, se hallusinoi metodin jota ei ole olemassa, jonka myötä kehitysserveri ei enää edes käynnistynyt. Heti alkuun siis se teki asioita, joissa ei ollut järkeä, joita minun piti korjata manuaalisesti - joskin hyödynsin myös eri tekoälyjä ongelmien korjauksessa. Tekoäly teki myös ihmeellisiä oletuksia liiketoimintalogiikassa, jotka piti korjata käsin.

### 3. Tärkeimmät tekemäni parannukset
- tietokannan initialisoimiseen liittyvän ongelman korjaus
- liiketoimintalogiikan järkeväksi tekeminen (esim. huoneiden maksimivarauksen pituus neljä tuntia tekoälyn valitseman _vuoden_ sijasta) 
- laajamittaisen testikirjaston teettäminen reunatapausten selvittämiseksi
- syötteen validoinnin ja puhdistamisen parantaminen (tekoälyn ensimmäinen versio esimerkiksi tarkasti vain merkkijonojen minimipituuden; minä määritin niille maksimipituudet jotta tietokanta pysyy siistinä)
- ohjelman kontitus (ei välttämätön, mutta helpottaa kehityksen jatkamista)

### Reflektio
Tehtävä oli riittävän yksinkertainen, että mielestäni tekoäly suoriutui siitä suhteellisen hyvin—joskin tekoälyn kanssa koodin tuottaminen ja ylläpito on ollut minulle tuttua jo pitkään, joten en osaa arvioida paljonko oma kokemukseni edesauttoi projektin etenemisessä. Oma panokseni prosessin valvojana oli kuitenkin täysin ratkaiseva, jotta ohjelma saatiin oikeasti toimimaan tarkoitetulla tavalla. 

Kirjasin tehtävään liittyvät tekniset oletukset tiedostoon OLETUKSET.md, joka löytyy repositorion juuresta.  
