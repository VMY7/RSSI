# === Importation des bibliothèques nécessaires ===
import streamlit as st                 # Pour l'interface web
import requests                        # Pour envoyer la requête à Ollama
import os                              # Pour parcourir les fichiers dans le dossier docs
import fitz                            # PyMuPDF : pour lire le texte à partir des fichiers PDF
import faiss                           # Pour faire de la recherche vectorielle rapide
import feedparser                      # Pour lire les flux RSS (ex : CERT-FR)
import json                            # 📦 pour sauvegarder dans un fichier JSON
from datetime import datetime
from sentence_transformers import SentenceTransformer  # Pour transformer textes/questions en vecteurs numériques

# === Configuration de la page Streamlit ===
st.set_page_config(
    page_title="Assistant RSSI",   # Titre de l’onglet navigateur
    page_icon="🛡️"                     # Icône de l’onglet navigateur
)

# === Titre et sous-titre de l’interface ===
st.title("🛡️ Assistant RSSI Virtuel")       # Titre principal
st.write("Pose une question liée à la cybersécurité, aux normes, ou aux incidents...")  # Petit texte explicatif

# === Chargement du modèle d’embedding (phrase → vecteur) ===
@st.cache_resource                        # Cache le modèle pour éviter de le recharger à chaque clic
def load_embedding_model():
    return SentenceTransformer('all-MiniLM-L6-v2')  # Petit modèle rapide et efficace pour le RAG

model = load_embedding_model()            # Chargement du modèle

# === Fonction pour lire tous les PDF, extraire le texte et le découper en chunks ===
def lire_et_chunker_pdfs(dossier="docs", taille_chunk=500, chevauchement=100):
    chunks = []      # Liste de tous les petits morceaux de texte
    metadatas = []   # Liste des fichiers d'origine pour chaque chunk

    for fichier in os.listdir(dossier):             # Parcours tous les fichiers du dossier
        if fichier.lower().endswith(".pdf"):        # On garde seulement les .pdf
            chemin = os.path.join(dossier, fichier) # Chemin complet du fichier

            try:
                doc = fitz.open(chemin)             # Ouvre le fichier PDF
                texte = ""
                for page in doc:                    # Parcourt chaque page
                    texte += page.get_text()        # Concatène le texte de la page

                # Découpe le texte en petits morceaux (chunks) de taille `taille_chunk`
                for i in range(0, len(texte), taille_chunk - chevauchement):
                    chunk = texte[i:i + taille_chunk]
                    if len(chunk.strip()) > 0:      # On évite les morceaux vides
                        chunks.append(chunk)        # On ajoute le chunk
                        metadatas.append(fichier)   # On garde en mémoire de quel fichier il vient

            except Exception as e:
                st.warning(f"Erreur de lecture de {fichier} : {e}")  # Affiche un message si erreur lecture PDF

    return chunks, metadatas  # Retourne les morceaux de texte + leur origine

# === Fonction pour encoder les chunks et construire l’index FAISS ===
def construire_index(chunks):
    vecteurs = model.encode(chunks)                  # Transforme chaque chunk en vecteur numérique
    index = faiss.IndexFlatL2(vecteurs.shape[1])     # Initialise un index FAISS (distance euclidienne)
    index.add(vecteurs)                              # Ajoute tous les vecteurs à l'index
    return index, vecteurs                           # Retourne l’index + les vecteurs (facultatif ici)

# === Fonction pour rechercher les passages les plus proches de la question ===
def rechercher_passages(question, chunks, index, top_k=3):
    vecteur_question = model.encode([question])       # Transforme la question en vecteur
    distances, indices = index.search(vecteur_question, top_k)  # Cherche les k chunks les plus proches
    passages = [chunks[i] for i in indices[0]]        # On extrait les chunks correspondants
    return passages                                   # Retourne les morceaux pertinents

# === Fonction pour récupérer les dernières alertes CERT-FR ===
def get_alertes_certfr():
    flux_url = "https://www.cert.ssi.gouv.fr/feed/"
    # flux_url = "https://www.cert.ssi.gouv.fr/avis/feed"

    feed = feedparser.parse(flux_url)

    # Trie les entrées par date de publication, de la plus récente à la plus ancienne
    articles_tries = sorted(
        feed.entries,
        key=lambda entry: entry.published_parsed,
        reverse=True
    )

    alertes = []
    for entry in articles_tries[:5]:  # Prend les 5 plus récents après tri
        alertes_securite = {
            "titre": entry.title,
            "date": entry.published,
            "description": entry.summary,
            "lien": entry.link
        }
        alertes.append(alertes_securite)

    return alertes
# === Fonction pour sauvegarder les échanges dans un fichier json ===
def sauvegarder_echange(question, reponse, fichier="conversations.jsonl"):
    echange = {
        "timestamp": datetime.now().isoformat(),
        "question": question,
        "reponse": reponse
    }

    with open(fichier, "a", encoding="utf-8") as f:
        f.write(json.dumps(echange, ensure_ascii=False) + "\n")

# === Fonction pour charger à chaque début de session l'historique des conversations stocké dans un json ===
def charger_historique_persistant(fichier="conversations.jsonl"):
    if not os.path.exists(fichier):
        return []

    historique = []
    with open(fichier, "r", encoding="utf-8") as f:
        for ligne in f:
            try:
                e = json.loads(ligne)
                historique.append({"question": e["question"], "reponse": e["reponse"]})
            except:
                continue

    return historique

# === Création des onglets Streamlit ===
onglets = st.tabs(["🧠 Assistant RSSI", "📝 Synthèse de document", "📡 Veille cybersécurité", "❓ FAQ cybersécurité", "📁 Ajouter un document", "📜 Historique"])

if "historique" not in st.session_state:
    st.session_state["historique"] = charger_historique_persistant()

# === Onglet 1 – Assistant RSSI ===
with onglets[0]:
    st.subheader("💬 Pose ta question")

    question = st.text_area("Ta question ❓", height=120)

    # Initialiser la mémoire si elle n'existe pas encore
    if "historique" not in st.session_state:
        st.session_state["historique"] = []  # C'est une liste vide au début

    if st.button("Envoyer"):
        
        if not question.strip():
            st.warning("Merci d’écrire une question.")    # Si zone vide → message

        else:
            with st.spinner("📚 Lecture des documents et génération de la réponse..."):

                try:
                    chunks, metadatas = lire_et_chunker_pdfs()
                    index, _ = construire_index(chunks)
                    passages_pertinents = rechercher_passages(question, chunks, index)

                    prompt = (
                        "Tu es un assistant RSSI spécialisé en cybersécurité.\n"
                        "Voici des extraits de documents de référence fournis par l'utilisateur. Utilise-les autant que possible pour répondre.\n"
                        "Tu peux aussi t'appuyer sur tes connaissances générales si nécessaire pour compléter ou clarifier la réponse.\n\n"
                    )
                    for i, passage in enumerate(passages_pertinents, 1):
                        prompt += f"Passage {i} :\n{passage}\n\n"

                    prompt += f"Question : {question}\n"
                    prompt += "Réponds de manière claire et précise en t’appuyant uniquement sur ces documents."

                    response = requests.post("http://localhost:11434/api/generate", json={
                        "model": "mistral",
                        "prompt": prompt,
                        "stream": False
                    })

                    answer = response.json().get("response", "❌ Pas de réponse générée.")
                    st.success("🧠 Réponse de l'assistant :")
                    st.markdown(answer)

                    # Sauvegarder la question et la réponse dans l'historique
                    st.session_state["historique"].append({
                        "question": question,
                        "reponse": answer
                    })
                    sauvegarder_echange(question, answer)

                except Exception as e:
                    st.error(f"❌ Erreur : {e}")

# === Onglet 2 – Synthèse de documents PDF ===
with onglets[1]:
    st.subheader("📝 Synthétiseur de documents cybersécurité")

    st.write("Téléverse un document PDF (rapport, guide, bulletin...) pour en obtenir une synthèse claire.")

    fichier_pdf = st.file_uploader("📄 Choisis un fichier PDF", type=["pdf"])

    if fichier_pdf is not None:
        try:
            # Lire le fichier PDF en mémoire avec PyMuPDF
            with fitz.open(stream=fichier_pdf.read(), filetype="pdf") as doc:
                contenu = ""
                for page in doc:
                    contenu += page.get_text()

            # Si le contenu est trop vide
            if len(contenu.strip()) < 100:
                st.warning("⚠️ Le document semble vide ou non lisible.")
            else:
                # Bouton pour lancer la synthèse
                if st.button("🧠 Générer une synthèse"):
                    with st.spinner("🤖 L'assistant lit le document et résume..."):
                        try:
                            prompt_synthese = (
                                "Tu es un expert cybersécurité.\n"
                                "Voici le contenu d’un document technique ou réglementaire :\n\n"
                                f"{contenu[:10000]}\n\n"  # On limite à 4000 caractères pour rester léger
                                "Fais un résumé clair, structuré et synthétique de ce document.\n"
                                "Mets en évidence les points clés, les menaces évoquées et les recommandations s’il y en a."
                            )

                            response = requests.post("http://localhost:11434/api/generate", json={
                                "model": "mistral",
                                "prompt": prompt_synthese,
                                "stream": False
                            })

                            reponse_synthese = response.json().get("response", "❌ Aucune réponse générée.")
                            st.success("✅ Synthèse générée :")
                            st.markdown(reponse_synthese)

                        except Exception as e:
                            st.error(f"❌ Erreur lors de la génération : {e}")
        except Exception as e:
            st.error(f"❌ Impossible de lire le PDF : {e}")

# === Onglet 3 – Veille cybersécurité ===
with onglets[2]:
    st.subheader("📡 Veille technologique sur la cybersécurité")

    st.info("Dernières alertes récupérées automatiquement depuis le CERT-FR :")

    # Appelle la fonction pour récupérer les alertes CERT-FR
    alertes = get_alertes_certfr()

    # Parcourt chaque alerte récupérée
    for idx, alerte in enumerate(alertes):
        st.markdown(f"### 🛡️ {alerte['titre']}")
        st.markdown(f"🗓️ *Date : {alerte['date']}*")
        st.write(alerte["description"])
        st.markdown(f"[🔗 Lire l'alerte complète]({alerte['lien']})")
        
        # Ajoute un bouton pour résumer cette alerte via LLM
        if st.button(f"🔄 Résumer cette alerte {idx}"):
            with st.spinner("🤖 Résumé en cours..."):

                try:
                    # Prépare un prompt de résumé
                    prompt_resume = (
                        "Fais un résumé clair et concis de cette alerte de cybersécurité.\n"
                        "Garde les points critiques et indique si c'est critique, modéré ou faible.\n\n"
                        f"Alerte : {alerte['description']}"
                    )

                    # Envoie au LLM local via Ollama
                    response = requests.post("http://localhost:11434/api/generate", json={
                        "model": "mistral",
                        "prompt": prompt_resume,
                        "stream": False
                    })

                    resume = response.json().get("response", "❌ Résumé impossible.")
                    st.success("Résumé de l'alerte :")
                    st.markdown(resume)

                except Exception as e:
                    st.error(f"❌ Erreur lors du résumé : {e}")

        st.markdown("---")  # Séparation entre les alertes

# === Onglet 4 – FAQ Cybersécurité ===
with onglets[3]:
    st.subheader("❓ Foire Aux Questions (FAQ) Cybersécurité")

    # Liste prédéfinie de questions fréquentes
    questions_faq = [
        "Pourquoi est-il important d'utiliser des mots de passe différents pour chaque compte ?",
        "Qu'est-ce qu'une authentification à deux facteurs (2FA) et pourquoi l'activer ?",
        "Pourquoi faut-il éviter de cliquer sur des liens suspects dans les emails ?",
        "Comment peut-on reconnaître un site sécurisé ?",
        "Pourquoi est-il essentiel de mettre à jour régulièrement ses logiciels et applications ?",
        "Qu'est-ce qu'un gestionnaire de mots de passe et pourquoi l'utiliser ?",
        "Pourquoi ne faut-il pas partager son mot de passe avec d'autres personnes ?",
        "Que faire si on reçoit un email étrange ou suspect ?",
        "Pourquoi faut-il faire attention aux informations partagées sur les réseaux sociaux ?",
        "Comment protéger son appareil avec un mot de passe ou une empreinte digitale ?",
        "Pourquoi faut-il éviter de se connecter à des réseaux Wi-Fi publics pour des transactions sensibles ?",
        "Comment vérifier si une application est sécurisée avant de la télécharger ?",
        "Pourquoi faut-il régulièrement sauvegarder ses données ?",
        "Qu'est-ce que le chiffrement et pourquoi est-il important ?",
        "Pourquoi est-il essentiel de se déconnecter de ses comptes après une session sur un ordinateur public ?"
    ]

    # Affiche chaque question avec un bouton pour demander la réponse
    for idx, question_faq in enumerate(questions_faq):
        if st.button(f"❓ {question_faq}", key=f"faq_{idx}"):
            with st.spinner("🤖 L'assistant réfléchit..."):
                try:
                    prompt_faq = (
                        "Tu es un expert en cybersécurité.\n"
                        "Réponds de façon claire, simple et concise à la question suivante :\n\n"
                        f"Question : {question_faq}"
                    )

                    response = requests.post("http://localhost:11434/api/generate", json={
                        "model": "mistral",
                        "prompt": prompt_faq,
                        "stream": False
                    })

                    reponse_faq = response.json().get("response", "❌ Pas de réponse générée.")
                    st.success("✅ Réponse de l'assistant :")
                    st.markdown(reponse_faq)

                except Exception as e:
                    st.error(f"❌ Erreur lors de la génération de réponse : {e}")

# === Onglet 5 – Ajouter un document PDF interne ===
with onglets[4]:
    st.subheader("📁 Ajouter un document interne au corpus")

    st.write("Tu peux ajouter un document PDF (ex : politique interne, rapport d'audit...).")

    fichier_ajout = st.file_uploader("📄 Sélectionne un fichier PDF à ajouter", type=["pdf"])

    if fichier_ajout is not None:
        if st.button("➕ Ajouter au corpus"):
            try:
                # Crée le dossier 'docs' s'il n'existe pas
                os.makedirs("docs", exist_ok=True)

                # Chemin complet du fichier à créer
                chemin_fichier = os.path.join("docs", fichier_ajout.name)

                # Écrit le fichier sur le disque
                with open(chemin_fichier, "wb") as f:
                    f.write(fichier_ajout.read())

                st.success(f"✅ Document '{fichier_ajout.name}' ajouté dans le dossier /docs avec succès !")
                st.info("Il sera utilisé automatiquement lors de la prochaine question posée à l'assistant.")

            except Exception as e:
                st.error(f"❌ Erreur lors de l’ajout du fichier : {e}")

# === Onglet 6 – Historique des échanges avec l'assistant ===
with onglets[5]:
    st.subheader("📜 Historique des échanges avec l'assistant")

    if st.session_state["historique"]:
        # Parcourt et affiche les échanges
        for idx, echange in enumerate(reversed(st.session_state["historique"])):
            st.markdown(f"### ❓ Question {len(st.session_state['historique']) - idx}")
            st.markdown(f"**Question :** {echange['question']}")
            st.markdown(f"**Réponse :** {echange['reponse']}")
            st.markdown("---")

        # === Bouton pour télécharger l'historique en JSON ===
        historique_json = json.dumps(st.session_state["historique"], indent=4, ensure_ascii=False)
        
        st.download_button(
            label="📥 Télécharger l'historique en JSON",
            data=historique_json,
            file_name="historique_questions.json",
            mime="application/json"
        )

    else:
        st.info("🕵️ Aucun échange enregistré pour l’instant. Pose une question pour démarrer !")