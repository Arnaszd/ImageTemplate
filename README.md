# Muzikos Viršelio Kūrėjas

Programa, skirta kurti muzikos viršelius su 9:16 santykiu, tinkamus socialinių tinklų istorijoms ir muzikos platformoms.

## Funkcijos

- Vaizdo įkėlimas ir automatinis pritaikymas 9:16 santykiui
- Centrinė kvadratinė vaizdo iškarpa su apvalintais kampais
- Pavadinimo ir atlikėjo teksto pridėjimas
- Progreso juosta ir medijos valdiklių vizualizacija
- **Dinaminis atnaujinimas** - peržiūra atsinaujina iš karto įvedus tekstą
- **Blur efekto reguliavimas** - galimybė keisti fono suliejimo intensyvumą
- Peržiūra realiu laiku
- Eksportavimas į PNG arba JPEG formatą

## Reikalavimai

- Python 3.6 arba naujesnė versija
- PyQt5
- Pillow (PIL)
- NumPy

## Diegimas

1. Įdiekite reikalingas bibliotekas:

```
pip install -r requirements.txt
```

## Naudojimas

1. Paleiskite programą:

```
python image_template_app.py
```

2. Paspauskite "Pasirinkti vaizdą" ir pasirinkite norimą vaizdą
3. Įveskite dainos pavadinimą ir atlikėjo vardą (peržiūra atsinaujins automatiškai)
4. Reguliuokite blur efekto intensyvumą slankikliu (numatytoji reikšmė - 60%)
5. Peržiūrėkite rezultatą dešiniajame skydelyje
6. Paspauskite "Eksportuoti" ir pasirinkite, kur išsaugoti galutinį vaizdą

## Pavyzdys

Programa sukuria vaizdą, panašų į muzikos grotuvo ekraną su jūsų pasirinktu fonu, dainos pavadinimu, atlikėju ir medijos valdikliais. Galutinis vaizdas yra 9:16 santykio, idealiai tinkantis socialinių tinklų istorijoms ir muzikos platformoms. 