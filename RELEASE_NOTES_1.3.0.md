# Project Odin 1.3.0

Livekonto har nu en gemensam **Manuell order**-panel för spotköp och spotförsäljning.
Säljlistan innehåller endast backend-godkända aktiva EUR-par där det anslutna
Kraken-kontot har ett positivt tillgängligt saldo.

Försäljningar kan anges som exakt kryptomängd eller som 25, 50, 75 eller 100 procent
av tillgängligt saldo. Reserverat saldo exkluderas alltid. Marknads- och limitorder
förhandsgranskas hos Kraken med `validate=true`; automatisk testning skickar aldrig
en riktig order.

Sälj-previewn visar saldo före och efter, kvantitet, procent, aktuellt eller valt
pris, uppskattad bruttointäkt, avgift, nettointäkt, riskgränser, pristidpunkt och
giltighetstid. Slutsteget kräver **Bekräfta riktig försäljning**. Föråldrade eller
använda previews, förändrade risker, otillräckligt saldo, inaktiverade par,
nödstopp och avstängt live-läge blockeras av backend.

Tillgångstabellen visar nu även pristidpunkt samt förberedda fält för genomsnittligt
inköpspris och uppskattat orealiserat resultat. När verifierat inköpspris saknas
visas **Inköpspris saknas** och inget resultat konstrueras.

Ingen automatisk handel, uttag, överföring, margin, hävstång, futures, staking eller
derivathandel har lagts till.
