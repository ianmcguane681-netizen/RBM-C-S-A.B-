"""What language the page speaks, and the rule that a missing translation is not English.

Going past one country breaks three things at once, and only one of them is the words. The
words are the visible part: a sample site for a bakery in Braga written in English is a
sample of somebody else's idea of their business. The other two are quieter — an address
printed in the wrong order looks like a mistake to the person who lives there, and an
outreach note that ignores the local rule on unsolicited mail is a different kind of
problem entirely.

This module handles the words and the address order. `countries.py` handles the rest.

## The rule

**A language this package has no strings for is `LANGUAGE_UNAVAILABLE`, never English.**
Falling back silently is the defect this whole codebase is arranged around, wearing its
most plausible disguise: the page still renders, it still looks finished, and the only sign
that anything went wrong is that a shop in Kraków has been sent a page in a language nobody
there asked for. So a missing locale stops the run for that business and says which
language was wanted.

## The second rule, which is about trust rather than defaults

**Only `en` is marked reviewed.** The other locales were written by the author of this
package, who is not a native speaker of any of them, and a translation nobody has checked
is not a translation you send to a stranger over your own name. They work, they are
grammatical as far as the author can tell, and every artefact built from an unreviewed
locale says in the brief and in the draft note that a native speaker must read it first.
Marking them reviewed is a one-line change per locale, made by whoever did the reading.

## What is never translated

The facts. A business's name, its street, its phone number and its opening hours are
printed exactly as the source carries them, in whatever language the source carries them
in. Translating `Rua da Boavista` into `Boavista Street` would be inventing an address, and
`name:en` is used only when OpenStreetMap itself carries one — in which case it is a fact
with a source like any other.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

LANGUAGE_AVAILABLE = "LANGUAGE_AVAILABLE"
LANGUAGE_UNAVAILABLE = "LANGUAGE_UNAVAILABLE"

LTR = "ltr"
RTL = "rtl"

#: Address orders that differ enough to look wrong to a local reader. `street_first` is
#: "12 Main Street, Donegal Town, F94 X2P8"; `number_last` is "Hauptstraße 12"; and
#: `postcode_first` puts the code before the town, as German and Austrian addresses do.
STREET_FIRST = "street_first"
NUMBER_LAST = "number_last"

#: Every locale must carry every one of these. A locale missing a key is a page with an
#: English sentence in the middle of it, which is the silent fallback in miniature, so it
#: is caught by a test rather than by a recipient.
REQUIRED = (
    "banner_lead", "banner_body", "not_affiliated_marker", "find_us", "opening_hours",
    "hours_note", "map_link", "missing_heading", "gap_photos_title", "gap_photos_body",
    "gap_words_title", "gap_words_body", "gap_services_title", "gap_services_body",
    "sources_intro", "attribution_note", "prepared_by", "stock_caption", "own_caption",
    "where_attached", "where_url",
    "stock_alt", "own_alt", "note_greeting", "note_body", "note_signoff",
    "claim_no_site_found", "claim_no_site_listed", "claim_social_only",
    "claim_domain_gone", "claim_unreachable", "claim_placeholder", "claim_no_viewport",
    "claim_no_https", "claim_generic",
)


@dataclass(frozen=True, slots=True)
class Locale:
    """One language's strings, and whether anybody who speaks it has read them."""

    code: str
    name: str
    strings: Mapping[str, str]
    direction: str = LTR
    address_order: str = STREET_FIRST
    postcode_before_city: bool = False
    reviewed: bool = False

    def text(self, key: str, **params) -> str:
        """A string with its parameters filled in.

        A missing key raises rather than returning the key or an empty string: an empty
        heading on a page looks like a design choice, and a raised error looks like the
        bug it is.
        """

        template = self.strings[key]
        return template.format(**params) if params else template

    @property
    def caveat(self) -> str:
        """What every artefact says about an unreviewed translation."""

        if self.reviewed:
            return ""
        return (f"The {self.name} strings in this package were not written by a native "
                f"speaker and nobody has reviewed them. Read the page and the note before "
                f"either goes to a business, or have somebody who speaks {self.name} do it.")


@dataclass(frozen=True, slots=True)
class LocaleChoice:
    """Which locale was chosen, how, and whether one was available at all."""

    status: str
    locale: Locale | None = None
    requested: str = ""
    reason: str = ""
    #: How the language was arrived at. Stated because "you asked for this" and "this is
    #: what people in that country usually speak" support different amounts of confidence.
    basis: str = ""

    def describe(self) -> str:
        if self.status == LANGUAGE_AVAILABLE and self.locale:
            line = f"LANGUAGE_AVAILABLE  {self.locale.code} ({self.locale.name}), {self.basis}"
            if not self.locale.reviewed:
                line += f"\n  UNREVIEWED: {self.locale.caveat}"
            return line
        return (f"LANGUAGE_UNAVAILABLE  {self.requested!r}\n  {self.reason}\n"
                f"  Nothing was built for this business. A page in a language this package "
                f"does not have strings for would have been an English page, which is not "
                f"the same thing and is worse than none.")


ENGLISH = {
    "banner_lead": "Unofficial sample.",
    "banner_body": ("This page was prepared by {operator} from publicly listed "
                    "information, as an example of what a site for {name} could look "
                    "like. It is not affiliated with, endorsed by, or connected to "
                    "{name}, and nothing on it was supplied by them."),
    "not_affiliated_marker": "not affiliated with",
    "find_us": "Find us",
    "opening_hours": "Opening hours",
    "hours_note": ("Recorded in the public listing in this form. Confirm before this page "
                   "goes anywhere near a customer."),
    "map_link": "View on the map",
    "missing_heading": "What is missing from this sample",
    "gap_photos_title": "Photographs you actually like",
    "gap_photos_body": ("What is here is either your own, taken from your site, or "
                        "labelled stock. Send better ones and they go straight in."),
    "gap_words_title": "A sentence about what you do",
    "gap_words_body": ("Written by you, or with you. Nothing on this page is invented, so "
                       "this space is left as it is."),
    "gap_services_title": "Services and prices",
    "gap_services_body": "The public listing does not carry them.",
    "sources_intro": "Every detail on this page came from a public source:",
    "attribution_note": ("Business details from OpenStreetMap contributors, available "
                         "under the Open Database Licence (ODbL). Photographs are either "
                         "the business's own, taken from their own public website and "
                         "shown back to them here, or stock photographs labelled as such "
                         "and credited above."),
    "prepared_by": ("Prepared by {operator}. Not published, not indexed, and yours to have "
                    "or to have taken down."),
    "stock_caption": "Stock photograph — not this business's premises.",
    "own_caption": "Your own photograph, from your website. Not republished anywhere.",
    "stock_alt": "Stock photograph",
    "own_alt": "Photograph from the business's own website",
    "where_attached": "in the attached file",
    "where_url": "at {url}",
    "note_greeting": "Hello,",
    "note_body": ("It is {where}. It is a sample rather than a finished site: the "
                  "details on it are the ones listed publicly, the photographs are either "
                  "yours or labelled stock, and the parts that need your words are marked "
                  "as gaps rather than filled in with guesses.\n\nIf it is useful, I will "
                  "finish it properly with you. If it is not, delete this and I will not "
                  "follow up."),
    "note_signoff": "",
    "claim_no_site_found": ("I could not find a website for you anywhere, so I built you "
                            "one to look at."),
    "claim_no_site_listed": ("I could not find a website listed for you in the public "
                             "directories, so I put together what one could look like. If "
                             "you already have one, ignore this with my apologies."),
    "claim_social_only": ("Your Facebook page is doing the job of a website at the moment, "
                          "so I put together what a site of your own could look like."),
    "claim_domain_gone": ("Your domain does not resolve at all any more — the registration "
                          "may have lapsed. I built a replacement you can look at."),
    "claim_unreachable": ("Your website did not load on either of two attempts today, so I "
                          "built a page that does."),
    "claim_placeholder": ("The address listed for your website shows a placeholder rather "
                          "than a site, so I built what could be there instead."),
    "claim_no_viewport": ("Your site is served to phones at desktop width, which is most of "
                          "the people looking for you. Here is the same information laid "
                          "out for a phone."),
    "claim_no_https": ("Your site is served over plain HTTP, so browsers show visitors a "
                       "'Not secure' warning before they read a word. Here is a version "
                       "without it."),
    "claim_generic": "I noticed a few fixable things about your site, and built an example.",
}


FRENCH = {
    "banner_lead": "Exemple non officiel.",
    "banner_body": ("Cette page a été préparée par {operator} à partir d'informations "
                    "publiques, comme exemple de ce à quoi pourrait ressembler un site "
                    "pour {name}. Elle n'est ni affiliée à {name}, ni approuvée par cette "
                    "entreprise, et aucun élément n'a été fourni par elle."),
    "not_affiliated_marker": "n'est ni affiliée",
    "find_us": "Nous trouver",
    "opening_hours": "Horaires d'ouverture",
    "hours_note": ("Enregistrés sous cette forme dans l'annuaire public. À vérifier avant "
                   "que cette page n'arrive devant un client."),
    "map_link": "Voir sur la carte",
    "missing_heading": "Ce qui manque à cet exemple",
    "gap_photos_title": "Des photos qui vous plaisent vraiment",
    "gap_photos_body": ("Celles qui figurent ici sont soit les vôtres, reprises de votre "
                        "site, soit des images d'illustration signalées comme telles. "
                        "Envoyez-en de meilleures et elles seront intégrées."),
    "gap_words_title": "Une phrase sur ce que vous faites",
    "gap_words_body": ("Écrite par vous, ou avec vous. Rien sur cette page n'est inventé, "
                       "cet espace reste donc vide."),
    "gap_services_title": "Prestations et tarifs",
    "gap_services_body": "L'annuaire public ne les indique pas.",
    "sources_intro": "Chaque information de cette page provient d'une source publique :",
    "attribution_note": ("Informations sur l'entreprise fournies par les contributeurs "
                         "d'OpenStreetMap, sous licence ODbL. Les photographies sont soit "
                         "celles de l'entreprise, reprises de son propre site public et "
                         "montrées ici, soit des images d'illustration signalées comme "
                         "telles et créditées ci-dessus."),
    "prepared_by": ("Préparé par {operator}. Ni publié, ni indexé : à vous de le garder ou "
                    "de le faire retirer."),
    "stock_caption": "Image d'illustration — il ne s'agit pas des locaux de cette entreprise.",
    "own_caption": "Votre propre photo, reprise de votre site. Republiée nulle part.",
    "stock_alt": "Image d'illustration",
    "own_alt": "Photo provenant du site de l'entreprise",
    "where_attached": "dans le fichier joint",
    "where_url": "ici : {url}",
    "note_greeting": "Bonjour,",
    "note_body": ("Elle se trouve {where}. C'est un exemple et non un site terminé : "
                  "les informations sont celles qui figurent publiquement, les photos sont "
                  "soit les vôtres soit des images d'illustration signalées comme telles, "
                  "et les parties qui demandent vos mots sont laissées vides plutôt que "
                  "remplies au hasard.\n\nSi cela vous est utile, je le terminerai avec "
                  "vous. Sinon, supprimez ce message : je ne relancerai pas."),
    "note_signoff": "",
    "claim_no_site_found": ("Je n'ai trouvé aucun site web pour vous, alors j'en ai "
                            "préparé un à regarder."),
    "claim_no_site_listed": ("Je n'ai trouvé aucun site web à votre nom dans les annuaires "
                             "publics, alors j'ai préparé ce à quoi il pourrait "
                             "ressembler. Si vous en avez déjà un, ignorez ce message et "
                             "veuillez m'excuser."),
    "claim_social_only": ("Votre page Facebook tient lieu de site web pour le moment, "
                          "alors j'ai préparé ce à quoi votre propre site pourrait "
                          "ressembler."),
    "claim_domain_gone": ("Votre nom de domaine ne répond plus du tout — l'enregistrement "
                          "a peut-être expiré. J'ai préparé un remplacement à regarder."),
    "claim_unreachable": ("Votre site ne s'est chargé lors d'aucune de mes deux tentatives "
                          "aujourd'hui, alors j'ai préparé une page qui fonctionne."),
    "claim_placeholder": ("L'adresse indiquée pour votre site affiche une page d'attente "
                          "plutôt qu'un site, alors j'ai préparé ce qui pourrait s'y "
                          "trouver."),
    "claim_no_viewport": ("Votre site s'affiche sur téléphone à la largeur d'un écran "
                          "d'ordinateur, alors que la plupart des gens vous cherchent "
                          "depuis un téléphone. Voici les mêmes informations mises en page "
                          "pour un mobile."),
    "claim_no_https": ("Votre site est servi en HTTP simple : les navigateurs affichent "
                       "donc « Non sécurisé » à vos visiteurs avant qu'ils n'aient lu un "
                       "mot. En voici une version sans cet avertissement."),
    "claim_generic": ("J'ai remarqué quelques points corrigibles sur votre site, et j'ai "
                      "préparé un exemple."),
}

SPANISH = {
    "banner_lead": "Ejemplo no oficial.",
    "banner_body": ("Esta página la preparó {operator} a partir de información pública, "
                    "como ejemplo de cómo podría ser un sitio para {name}. No está "
                    "afiliada a {name} ni cuenta con su respaldo, y la empresa no ha "
                    "aportado nada de lo que aquí aparece."),
    "not_affiliated_marker": "no está afiliada",
    "find_us": "Dónde estamos",
    "opening_hours": "Horario",
    "hours_note": ("Registrado así en el directorio público. Confírmelo antes de que esta "
                   "página llegue a un cliente."),
    "map_link": "Ver en el mapa",
    "missing_heading": "Lo que falta en este ejemplo",
    "gap_photos_title": "Fotos que de verdad le gusten",
    "gap_photos_body": ("Las que hay aquí son suyas, tomadas de su web, o imágenes de "
                        "archivo señaladas como tales. Envíe mejores y se colocan."),
    "gap_words_title": "Una frase sobre lo que hacen",
    "gap_words_body": ("Escrita por usted, o con usted. En esta página no hay nada "
                       "inventado, así que este espacio se queda vacío."),
    "gap_services_title": "Servicios y precios",
    "gap_services_body": "El directorio público no los recoge.",
    "sources_intro": "Cada dato de esta página procede de una fuente pública:",
    "attribution_note": ("Datos del negocio aportados por colaboradores de OpenStreetMap, "
                         "bajo licencia ODbL. Las fotografías son del propio negocio, "
                         "tomadas de su web pública y mostradas aquí, o imágenes de "
                         "archivo señaladas como tales y acreditadas arriba."),
    "prepared_by": ("Preparado por {operator}. Ni publicado ni indexado: es suyo, para "
                    "quedárselo o para que lo retire."),
    "stock_caption": "Imagen de archivo — no es el local de este negocio.",
    "own_caption": "Su propia foto, tomada de su web. No se republica en ningún sitio.",
    "stock_alt": "Imagen de archivo",
    "own_alt": "Foto de la web del propio negocio",
    "where_attached": "en el archivo adjunto",
    "where_url": "en {url}",
    "note_greeting": "Hola:",
    "note_body": ("Está {where}. Es un ejemplo, no un sitio terminado: los datos son "
                  "los que figuran públicamente, las fotos son suyas o de archivo "
                  "señaladas como tales, y las partes que necesitan sus palabras están "
                  "marcadas como huecos en lugar de rellenarse a base de suposiciones."
                  "\n\nSi le sirve, lo termino con usted. Si no, borre esto y no volveré a "
                  "insistir."),
    "note_signoff": "",
    "claim_no_site_found": ("No he encontrado ninguna web suya por ninguna parte, así que "
                            "le he preparado una para que la vea."),
    "claim_no_site_listed": ("No he encontrado ninguna web a su nombre en los directorios "
                             "públicos, así que he preparado cómo podría ser una. Si ya "
                             "tiene una, ignore esto y disculpe la molestia."),
    "claim_social_only": ("Ahora mismo su página de Facebook hace las veces de web, así "
                          "que he preparado cómo podría ser un sitio propio."),
    "claim_domain_gone": ("Su dominio ya no resuelve: es posible que el registro haya "
                          "caducado. Le he preparado un sustituto para que lo vea."),
    "claim_unreachable": ("Su web no cargó en ninguno de los dos intentos de hoy, así que "
                          "he preparado una página que sí carga."),
    "claim_placeholder": ("La dirección que consta como su web muestra una página "
                          "provisional en lugar de un sitio, así que he preparado lo que "
                          "podría haber ahí."),
    "claim_no_viewport": ("Su web se sirve al móvil con el ancho de un ordenador, y desde "
                          "el móvil le busca la mayoría de la gente. Aquí está la misma "
                          "información maquetada para el teléfono."),
    "claim_no_https": ("Su web se sirve por HTTP sin cifrar, así que el navegador avisa a "
                       "sus visitantes de que «no es segura» antes de que lean una "
                       "palabra. Aquí tiene una versión sin ese aviso."),
    "claim_generic": ("He visto algunas cosas de su web que tienen arreglo fácil, y he "
                      "preparado un ejemplo."),
}

GERMAN = {
    "banner_lead": "Inoffizielles Beispiel.",
    "banner_body": ("Diese Seite wurde von {operator} aus öffentlich verfügbaren Angaben "
                    "erstellt, als Beispiel dafür, wie eine Website für {name} aussehen "
                    "könnte. Sie ist nicht mit {name} verbunden und nicht von dort "
                    "genehmigt; nichts darauf stammt von dem Betrieb selbst."),
    "not_affiliated_marker": "nicht mit",
    "find_us": "So finden Sie uns",
    "opening_hours": "Öffnungszeiten",
    "hours_note": ("In dieser Form im öffentlichen Verzeichnis eingetragen. Bitte prüfen, "
                   "bevor diese Seite einem Kunden begegnet."),
    "map_link": "Auf der Karte ansehen",
    "missing_heading": "Was in diesem Beispiel fehlt",
    "gap_photos_title": "Fotos, die Ihnen wirklich gefallen",
    "gap_photos_body": ("Die hier gezeigten sind entweder Ihre eigenen, von Ihrer Website "
                        "übernommen, oder als solche gekennzeichnete Stockfotos. Schicken "
                        "Sie bessere, dann kommen die hinein."),
    "gap_words_title": "Ein Satz darüber, was Sie tun",
    "gap_words_body": ("Von Ihnen geschrieben, oder mit Ihnen. Auf dieser Seite ist nichts "
                       "erfunden, deshalb bleibt diese Stelle leer."),
    "gap_services_title": "Leistungen und Preise",
    "gap_services_body": "Das öffentliche Verzeichnis führt sie nicht.",
    "sources_intro": "Jede Angabe auf dieser Seite stammt aus einer öffentlichen Quelle:",
    "attribution_note": ("Betriebsangaben von OpenStreetMap-Mitwirkenden, verfügbar unter "
                         "der Open Database Licence (ODbL). Die Fotos stammen entweder vom "
                         "Betrieb selbst, übernommen von dessen öffentlicher Website und "
                         "hier zurückgezeigt, oder es sind gekennzeichnete Stockfotos, die "
                         "oben genannt sind."),
    "prepared_by": ("Erstellt von {operator}. Nicht veröffentlicht, nicht indexiert — "
                    "Ihres, zum Behalten oder zum Entfernenlassen."),
    "stock_caption": "Stockfoto — nicht die Räume dieses Betriebs.",
    "own_caption": "Ihr eigenes Foto, von Ihrer Website. Wird nirgends neu veröffentlicht.",
    "stock_alt": "Stockfoto",
    "own_alt": "Foto von der Website des Betriebs",
    "where_attached": "in der angehängten Datei",
    "where_url": "unter {url}",
    "note_greeting": "Guten Tag,",
    "note_body": ("Sie liegt {where}. Es ist ein Beispiel, keine fertige Website: "
                  "die Angaben sind die öffentlich eingetragenen, die Fotos sind entweder "
                  "Ihre oder gekennzeichnete Stockfotos, und die Stellen, an denen Ihre "
                  "Worte stehen müssten, sind als Lücken markiert statt geraten."
                  "\n\nWenn es Ihnen nützt, mache ich es mit Ihnen fertig. Wenn nicht, "
                  "löschen Sie das hier; ich hake nicht nach."),
    "note_signoff": "",
    "claim_no_site_found": ("Ich habe nirgends eine Website von Ihnen gefunden und Ihnen "
                            "deshalb eine gebaut, die Sie sich ansehen können."),
    "claim_no_site_listed": ("In den öffentlichen Verzeichnissen ist für Sie keine Website "
                             "eingetragen, deshalb habe ich zusammengestellt, wie eine "
                             "aussehen könnte. Falls Sie längst eine haben, ignorieren Sie "
                             "das hier bitte."),
    "claim_social_only": ("Ihre Facebook-Seite übernimmt derzeit die Rolle einer Website, "
                          "deshalb habe ich zusammengestellt, wie eine eigene aussehen "
                          "könnte."),
    "claim_domain_gone": ("Ihre Domain löst überhaupt nicht mehr auf — möglicherweise ist "
                          "die Registrierung ausgelaufen. Ich habe einen Ersatz gebaut."),
    "claim_unreachable": ("Ihre Website hat heute bei zwei Versuchen nicht geladen, "
                          "deshalb habe ich eine Seite gebaut, die lädt."),
    "claim_placeholder": ("Unter der eingetragenen Adresse steht eine Platzhalterseite "
                          "statt einer Website, deshalb habe ich gebaut, was dort stehen "
                          "könnte."),
    "claim_no_viewport": ("Ihre Website wird auf dem Handy in Desktop-Breite ausgeliefert "
                          "— und über das Handy sucht Sie die Mehrheit. Hier sind dieselben "
                          "Angaben fürs Telefon gesetzt."),
    "claim_no_https": ("Ihre Website läuft über einfaches HTTP, deshalb warnen Browser "
                       "Ihre Besucher mit „Nicht sicher“, bevor die ein Wort gelesen "
                       "haben. Hier ist eine Fassung ohne diese Warnung."),
    "claim_generic": ("Mir sind ein paar leicht behebbare Dinge an Ihrer Website "
                      "aufgefallen, und ich habe ein Beispiel gebaut."),
}


ITALIAN = {
    "banner_lead": "Esempio non ufficiale.",
    "banner_body": ("Questa pagina è stata preparata da {operator} a partire da "
                    "informazioni pubbliche, come esempio di come potrebbe essere un sito "
                    "per {name}. Non è affiliata a {name} né approvata da {name}, e nulla "
                    "di ciò che vi compare è stato fornito dall'attività."),
    "not_affiliated_marker": "non è affiliata",
    "find_us": "Dove siamo",
    "opening_hours": "Orari di apertura",
    "hours_note": ("Registrati in questa forma nell'elenco pubblico. Da verificare prima "
                   "che questa pagina arrivi davanti a un cliente."),
    "map_link": "Vedi sulla mappa",
    "missing_heading": "Che cosa manca in questo esempio",
    "gap_photos_title": "Foto che vi piacciano davvero",
    "gap_photos_body": ("Quelle qui presenti sono vostre, riprese dal vostro sito, oppure "
                        "immagini di repertorio segnalate come tali. Mandatene di migliori "
                        "e vanno subito al loro posto."),
    "gap_words_title": "Una frase su quello che fate",
    "gap_words_body": ("Scritta da voi, o con voi. In questa pagina non c'è nulla di "
                       "inventato, perciò questo spazio resta vuoto."),
    "gap_services_title": "Servizi e prezzi",
    "gap_services_body": "L'elenco pubblico non li riporta.",
    "sources_intro": "Ogni dato di questa pagina proviene da una fonte pubblica:",
    "attribution_note": ("Dati dell'attività forniti dai contributori di OpenStreetMap, "
                         "disponibili con licenza ODbL. Le fotografie sono dell'attività "
                         "stessa, riprese dal suo sito pubblico e mostrate qui, oppure "
                         "immagini di repertorio segnalate come tali e accreditate sopra."),
    "prepared_by": ("Preparato da {operator}. Non pubblicato, non indicizzato: è vostro, "
                    "da tenere o da far rimuovere."),
    "stock_caption": "Immagine di repertorio — non sono i locali di questa attività.",
    "own_caption": "Una vostra foto, ripresa dal vostro sito. Non ripubblicata da nessuna parte.",
    "stock_alt": "Immagine di repertorio",
    "own_alt": "Foto dal sito dell'attività",
    "where_attached": "nel file allegato",
    "where_url": "qui: {url}",
    "note_greeting": "Buongiorno,",
    "note_body": ("Si trova {where}. È un esempio, non un sito finito: i dati sono "
                  "quelli pubblicati negli elenchi, le foto sono vostre oppure di "
                  "repertorio segnalate come tali, e le parti che richiedono parole vostre "
                  "sono lasciate come spazi vuoti anziché riempite a caso.\n\nSe vi è "
                  "utile, lo finisco insieme a voi. Se non lo è, cancellate pure questo "
                  "messaggio: non insisterò."),
    "note_signoff": "",
    "claim_no_site_found": ("Non ho trovato da nessuna parte un sito web vostro, così ne "
                            "ho preparato uno da guardare."),
    "claim_no_site_listed": ("Negli elenchi pubblici non risulta alcun sito web a vostro "
                             "nome, così ho preparato come potrebbe essere. Se ne avete "
                             "già uno, ignorate pure questo messaggio."),
    "claim_social_only": ("Al momento la vostra pagina Facebook fa le veci di un sito, "
                          "così ho preparato come potrebbe essere un sito vostro."),
    "claim_domain_gone": ("Il vostro dominio non risolve più — la registrazione potrebbe "
                          "essere scaduta. Ho preparato un sostituto da guardare."),
    "claim_unreachable": ("Il vostro sito non si è caricato in nessuno dei due tentativi "
                          "di oggi, così ho preparato una pagina che si carica."),
    "claim_placeholder": ("All'indirizzo indicato come vostro sito compare una pagina "
                          "provvisoria anziché un sito, così ho preparato quello che "
                          "potrebbe esserci."),
    "claim_no_viewport": ("Il vostro sito viene servito al telefono con la larghezza di un "
                          "computer, ed è dal telefono che vi cerca la maggior parte delle "
                          "persone. Ecco le stesse informazioni impaginate per il "
                          "cellulare."),
    "claim_no_https": ("Il vostro sito viaggia su HTTP semplice, perciò i browser mostrano "
                       "ai visitatori l'avviso «non sicuro» prima ancora che leggano una "
                       "parola. Ecco una versione senza quell'avviso."),
    "claim_generic": ("Ho notato alcune cose facilmente sistemabili sul vostro sito, e ho "
                      "preparato un esempio."),
}

PORTUGUESE = {
    "banner_lead": "Exemplo não oficial.",
    "banner_body": ("Esta página foi preparada por {operator} a partir de informação "
                    "pública, como exemplo do que poderia ser um site para {name}. Não "
                    "está associada a {name} nem foi aprovada por {name}, e nada do que "
                    "aqui aparece foi fornecido pelo negócio."),
    "not_affiliated_marker": "não está associada",
    "find_us": "Onde estamos",
    "opening_hours": "Horário",
    "hours_note": ("Registado desta forma no directório público. Confirme antes de esta "
                   "página chegar a um cliente."),
    "map_link": "Ver no mapa",
    "missing_heading": "O que falta neste exemplo",
    "gap_photos_title": "Fotografias de que goste mesmo",
    "gap_photos_body": ("As que aqui estão são suas, retiradas do seu site, ou imagens de "
                        "banco assinaladas como tal. Envie melhores e entram de imediato."),
    "gap_words_title": "Uma frase sobre o que fazem",
    "gap_words_body": ("Escrita por si, ou consigo. Nada nesta página é inventado, por "
                       "isso este espaço fica vazio."),
    "gap_services_title": "Serviços e preços",
    "gap_services_body": "O directório público não os indica.",
    "sources_intro": "Cada dado desta página vem de uma fonte pública:",
    "attribution_note": ("Dados do negócio fornecidos por colaboradores do OpenStreetMap, "
                         "disponíveis sob a licença ODbL. As fotografias são do próprio "
                         "negócio, retiradas do seu site público e aqui mostradas, ou "
                         "imagens de banco assinaladas como tal e creditadas acima."),
    "prepared_by": ("Preparado por {operator}. Não publicado, não indexado — é seu, para "
                    "ficar ou para mandar retirar."),
    "stock_caption": "Imagem de banco — não são as instalações deste negócio.",
    "own_caption": "Uma fotografia sua, retirada do seu site. Não republicada em lado nenhum.",
    "stock_alt": "Imagem de banco",
    "own_alt": "Fotografia do site do próprio negócio",
    "where_attached": "no ficheiro em anexo",
    "where_url": "em {url}",
    "note_greeting": "Olá,",
    "note_body": ("Está {where}. É um exemplo e não um site terminado: os dados são os "
                  "que constam publicamente, as fotografias são suas ou de banco "
                  "assinaladas como tal, e as partes que precisam das suas palavras estão "
                  "marcadas como espaços em vez de preenchidas por suposição.\n\nSe lhe "
                  "for útil, termino-o consigo. Se não for, apague isto — não voltarei a "
                  "insistir."),
    "note_signoff": "",
    "claim_no_site_found": ("Não encontrei nenhum site seu em lado nenhum, por isso "
                            "preparei-lhe um para ver."),
    "claim_no_site_listed": ("Não encontrei nenhum site em seu nome nos directórios "
                             "públicos, por isso preparei o que poderia ser um. Se já "
                             "tiver um, ignore isto e as minhas desculpas."),
    "claim_social_only": ("De momento a sua página de Facebook faz as vezes de site, por "
                          "isso preparei o que poderia ser um site seu."),
    "claim_domain_gone": ("O seu domínio já não resolve — o registo pode ter expirado. "
                          "Preparei um substituto para ver."),
    "claim_unreachable": ("O seu site não carregou em nenhuma das duas tentativas de hoje, "
                          "por isso preparei uma página que carrega."),
    "claim_placeholder": ("O endereço indicado como sendo o seu site mostra uma página "
                          "provisória em vez de um site, por isso preparei o que lá poderia "
                          "estar."),
    "claim_no_viewport": ("O seu site é servido ao telemóvel com a largura de um "
                          "computador, e é pelo telemóvel que a maioria das pessoas o "
                          "procura. Aqui está a mesma informação composta para telefone."),
    "claim_no_https": ("O seu site é servido em HTTP simples, por isso os navegadores "
                       "avisam os visitantes de que «não é seguro» antes de lerem uma "
                       "palavra. Aqui está uma versão sem esse aviso."),
    "claim_generic": ("Reparei nalgumas coisas facilmente corrigíveis no seu site, e "
                      "preparei um exemplo."),
}

DUTCH = {
    "banner_lead": "Onofficieel voorbeeld.",
    "banner_body": ("Deze pagina is gemaakt door {operator} op basis van openbaar "
                    "vermelde gegevens, als voorbeeld van hoe een website voor {name} "
                    "eruit zou kunnen zien. Ze is niet verbonden aan {name} en niet door "
                    "{name} goedgekeurd; niets erop is door het bedrijf aangeleverd."),
    "not_affiliated_marker": "niet verbonden aan",
    "find_us": "Waar u ons vindt",
    "opening_hours": "Openingstijden",
    "hours_note": ("Zo vastgelegd in het openbare register. Controleer dit voordat deze "
                   "pagina bij een klant terechtkomt."),
    "map_link": "Bekijk op de kaart",
    "missing_heading": "Wat er in dit voorbeeld ontbreekt",
    "gap_photos_title": "Foto's die u echt goed vindt",
    "gap_photos_body": ("Wat hier staat is van uzelf, overgenomen van uw site, of een als "
                        "zodanig gemarkeerde stockfoto. Stuur betere en ze gaan er meteen "
                        "in."),
    "gap_words_title": "Een zin over wat u doet",
    "gap_words_body": ("Door u geschreven, of samen met u. Niets op deze pagina is "
                       "verzonnen, dus deze plek blijft leeg."),
    "gap_services_title": "Diensten en prijzen",
    "gap_services_body": "Het openbare register vermeldt ze niet.",
    "sources_intro": "Elk gegeven op deze pagina komt uit een openbare bron:",
    "attribution_note": ("Bedrijfsgegevens van OpenStreetMap-bijdragers, beschikbaar onder "
                         "de Open Database Licence (ODbL). De foto's zijn van het bedrijf "
                         "zelf, overgenomen van de eigen openbare website en hier "
                         "teruggetoond, of stockfoto's die als zodanig zijn gemarkeerd en "
                         "hierboven zijn vermeld."),
    "prepared_by": ("Gemaakt door {operator}. Niet gepubliceerd, niet geïndexeerd — van u, "
                    "om te houden of te laten verwijderen."),
    "stock_caption": "Stockfoto — dit is niet het pand van dit bedrijf.",
    "own_caption": "Uw eigen foto, van uw website. Wordt nergens opnieuw gepubliceerd.",
    "stock_alt": "Stockfoto",
    "own_alt": "Foto van de eigen website van het bedrijf",
    "where_attached": "in het bijgevoegde bestand",
    "where_url": "op {url}",
    "note_greeting": "Goedendag,",
    "note_body": ("U vindt hem {where}. Het is een voorbeeld en geen afgeronde website: "
                  "de gegevens zijn de openbaar vermelde, de foto's zijn van u of "
                  "gemarkeerde stockfoto's, en de delen waar uw eigen woorden horen zijn "
                  "als lege plek gemarkeerd in plaats van ingevuld met gissingen.\n\nAls u "
                  "er iets aan hebt, maak ik hem samen met u af. Zo niet, verwijder dit "
                  "dan; ik kom er niet op terug."),
    "note_signoff": "",
    "claim_no_site_found": ("Ik kon nergens een website van u vinden, dus heb ik er een "
                            "gemaakt om naar te kijken."),
    "claim_no_site_listed": ("In de openbare registers staat geen website op uw naam, dus "
                             "heb ik in elkaar gezet hoe er een uit zou kunnen zien. Hebt "
                             "u er al een, negeer dit dan met mijn excuses."),
    "claim_social_only": ("Uw Facebookpagina doet op dit moment het werk van een website, "
                          "dus heb ik in elkaar gezet hoe een eigen site eruit zou kunnen "
                          "zien."),
    "claim_domain_gone": ("Uw domein reageert helemaal niet meer — mogelijk is de "
                          "registratie verlopen. Ik heb een vervanging gemaakt om naar te "
                          "kijken."),
    "claim_unreachable": ("Uw website laadde vandaag bij geen van twee pogingen, dus heb "
                          "ik een pagina gemaakt die dat wel doet."),
    "claim_placeholder": ("Op het adres dat als uw website vermeld staat, verschijnt een "
                          "tijdelijke pagina in plaats van een site, dus heb ik gemaakt "
                          "wat daar zou kunnen staan."),
    "claim_no_viewport": ("Uw site wordt op een telefoon op desktopbreedte getoond, en via "
                          "de telefoon zoekt het merendeel u op. Hier staat dezelfde "
                          "informatie opgemaakt voor een telefoon."),
    "claim_no_https": ("Uw site loopt over gewoon HTTP, dus browsers waarschuwen "
                       "bezoekers met 'niet veilig' voordat ze een woord gelezen hebben. "
                       "Hier is een versie zonder die waarschuwing."),
    "claim_generic": ("Er vielen me een paar makkelijk te verhelpen dingen op aan uw site, "
                      "en ik heb een voorbeeld gemaakt."),
}

IRISH = {
    "banner_lead": "Sampla neamhoifigiúil.",
    "banner_body": ("Rinne {operator} an leathanach seo as eolas atá ar fáil go poiblí, "
                    "mar shampla den chuma a d'fhéadfadh a bheith ar shuíomh do {name}. "
                    "Níl sé ceangailte le {name} ná ceadaithe ag {name}, agus níor chuir "
                    "an gnó féin aon rud ar fáil dó."),
    "not_affiliated_marker": "níl sé ceangailte le",
    "find_us": "Teacht orainn",
    "opening_hours": "Uaireanta oscailte",
    "hours_note": ("Taifeadta sa bhfoirm seo sa liosta poiblí. Deimhnigh iad sula "
                   "bhfeiceann custaiméir an leathanach seo."),
    "map_link": "Féach ar an léarscáil",
    "missing_heading": "Cad atá in easnamh ar an sampla seo",
    "gap_photos_title": "Grianghraif a thaitníonn leat i ndáiríre",
    "gap_photos_body": ("Is leatsa iad na cinn atá anseo, tógtha ó do shuíomh féin, nó is "
                        "grianghraif stoic iad atá marcáilte mar sin. Seol cinn níos fearr "
                        "agus cuirfear isteach iad."),
    "gap_words_title": "Abairt faoin obair a dhéanann sibh",
    "gap_words_body": ("Scríofa agatsa, nó leatsa. Níl aon rud cumtha ar an leathanach "
                       "seo, agus mar sin fágtar an spás seo folamh."),
    "gap_services_title": "Seirbhísí agus praghsanna",
    "gap_services_body": "Níl siad sa liosta poiblí.",
    "sources_intro": "Tháinig gach sonra ar an leathanach seo ó fhoinse phoiblí:",
    "attribution_note": ("Sonraí gnó ó rannpháirtithe OpenStreetMap, ar fáil faoin Open "
                         "Database Licence (ODbL). Is leis an ngnó féin na grianghraif, "
                         "tógtha óna suíomh poiblí féin agus taispeánta ar ais anseo, nó "
                         "is grianghraif stoic iad atá marcáilte mar sin agus creidiúnaithe "
                         "thuas."),
    "prepared_by": ("Ullmhaithe ag {operator}. Níl sé foilsithe ná innéacsaithe — is leatsa "
                    "é, le coinneáil nó le baint anuas."),
    "stock_caption": "Grianghraf stoic — ní hé áitreabh an ghnó seo atá ann.",
    "own_caption": "Do ghrianghraf féin, ó do shuíomh. Níl sé athfhoilsithe áit ar bith.",
    "stock_alt": "Grianghraf stoic",
    "own_alt": "Grianghraf ó shuíomh an ghnó féin",
    "where_attached": "sa chomhad atá ceangailte",
    "where_url": "ag {url}",
    "note_greeting": "Dia duit,",
    "note_body": ("Tá sé {where}. Sampla atá ann seachas suíomh críochnaithe: is iad na "
                  "sonraí atá liostaithe go poiblí atá air, is leatsa na grianghraif nó is "
                  "grianghraif stoic mharcáilte iad, agus tá na codanna a bhfuil do chuid "
                  "focal féin ag teastáil uathu fágtha folamh seachas líonta le buille faoi "
                  "thuairim.\n\nMá tá sé ina chabhair, críochnóidh mé i gceart leat é. Mura "
                  "bhfuil, scrios é seo agus ní chuirfidh mé isteach ort arís."),
    "note_signoff": "",
    "claim_no_site_found": ("Níor éirigh liom suíomh gréasáin a aimsiú duit in aon áit, "
                            "agus mar sin thóg mé ceann duit le breathnú air."),
    "claim_no_site_listed": ("Níl aon suíomh gréasáin luaite leat sna liostaí poiblí, agus "
                             "mar sin chuir mé le chéile an chuma a d'fhéadfadh a bheith ar "
                             "cheann. Má tá ceann agat cheana, déan neamhaird air seo agus "
                             "gabh mo leithscéal."),
    "claim_social_only": ("Tá do leathanach Facebook ag déanamh obair suímh faoi láthair, "
                          "agus mar sin chuir mé le chéile an chuma a d'fhéadfadh a bheith "
                          "ar shuíomh de do chuid féin."),
    "claim_domain_gone": ("Níl d'fhearann ag freagairt ar chor ar bith a thuilleadh — "
                          "seans gur imigh an clárú in éag. Thóg mé ionadaí duit le "
                          "breathnú air."),
    "claim_unreachable": ("Níor lódáil do shuíomh ar cheachtar den dá iarracht inniu, agus "
                          "mar sin thóg mé leathanach a lódálann."),
    "claim_placeholder": ("Ag an seoladh atá luaite le do shuíomh tá leathanach sealadach "
                          "seachas suíomh, agus mar sin thóg mé an rud a d'fhéadfadh a "
                          "bheith ann."),
    "claim_no_viewport": ("Cuirtear do shuíomh chuig fóin ar leithead ríomhaire, agus is ar "
                          "an bhfón atá formhór na ndaoine do do chuardach. Seo an t-eolas "
                          "céanna leagtha amach don fhón."),
    "claim_no_https": ("Cuirtear do shuíomh ar fáil trí HTTP simplí, agus mar sin "
                       "tugann brabhsálaithe rabhadh 'Not secure' do chuairteoirí sula "
                       "léann siad focal. Seo leagan gan an rabhadh sin."),
    "claim_generic": ("Thug mé faoi deara cúpla rud atá inseasctha ar do shuíomh, agus "
                      "thóg mé sampla."),
}


#: Every language this package can build a page in. Adding one is a dict and a row here;
#: there is deliberately no machine translation step, because a page in a language nobody
#: involved can read is a page nobody can check, and the check is the product.
CATALOGUE: dict[str, Locale] = {
    "en": Locale("en", "English", ENGLISH, reviewed=True),
    "ga": Locale("ga", "Irish", IRISH),
    "fr": Locale("fr", "French", FRENCH),
    "es": Locale("es", "Spanish", SPANISH),
    "de": Locale("de", "German", GERMAN, address_order=NUMBER_LAST,
                 postcode_before_city=True),
    "it": Locale("it", "Italian", ITALIAN, address_order=NUMBER_LAST,
                 postcode_before_city=True),
    "pt": Locale("pt", "Portuguese", PORTUGUESE),
    "nl": Locale("nl", "Dutch", DUTCH, address_order=NUMBER_LAST),
}


def choose(requested: str = "", *, country_languages: tuple[str, ...] = (),
           country: str = "") -> LocaleChoice:
    """Which language to build in, and on what basis.

    An explicit request wins and is honoured or refused — never quietly swapped for
    something else. With no request, the country's own languages are tried in order, and
    the basis says so, because "you asked for German" and "Austria mostly speaks German"
    are different amounts of confidence and the brief prints which one applied.
    """

    if requested:
        locale = CATALOGUE.get(requested.lower())
        if locale is None:
            return LocaleChoice(
                LANGUAGE_UNAVAILABLE, requested=requested,
                reason=(f"this package has no strings for {requested!r}. It has: "
                        f"{', '.join(sorted(CATALOGUE))}. Add them in locales.py — there "
                        f"is no machine translation step, on purpose."))
        return LocaleChoice(LANGUAGE_AVAILABLE, locale, requested, basis="you asked for it")

    for code in country_languages:
        locale = CATALOGUE.get(code)
        if locale is not None:
            return LocaleChoice(LANGUAGE_AVAILABLE, locale, code,
                                basis=f"the usual language of business in {country or code}")
    if country_languages:
        return LocaleChoice(
            LANGUAGE_UNAVAILABLE, requested=country_languages[0],
            reason=(f"{country or 'that country'} usually does business in "
                    f"{', '.join(country_languages)}, and this package has strings for "
                    f"none of them. Pass --language to override, or add the strings."))
    return LocaleChoice(
        LANGUAGE_UNAVAILABLE, requested="",
        reason=("no language was requested and the country could not be established, so "
                "there is nothing to pick from. English is not the default: a page in the "
                "wrong language is worse than no page."))
