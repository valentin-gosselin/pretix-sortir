// JavaScript pour le plugin Sortir!
// Version: 2025-10-28-15:30 - Fix: suppression des champs quand quantité diminue

// FONCTION GLOBALE DE BLOCAGE - Intercepte TOUS les clics
window.sortirBlockerActive = false;
window.sortirValidationRequired = false;

document.addEventListener('click', function(e) {
    if (window.sortirValidationRequired && !window.sortirBlockerActive) {
        var target = e.target;
        // Vérifie si c'est un bouton d'ajout au panier
        if (target && (
            target.textContent.includes('panier') ||
            target.textContent.includes('Panier') ||
            target.textContent.includes('cart') ||
            target.textContent.includes('Cart') ||
            target.textContent.includes('Ajouter') ||
            target.classList.contains('btn-primary') ||
            target.classList.contains('btn-success')
        )) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            // Pas d'alerte, le bouton grisé suffit
            return false;
        }
    }
}, true); // Capture phase pour intercepter en premier

document.addEventListener('DOMContentLoaded', function() {

    // PERSISTANCE DES VALEURS VALIDÉES - Utilise sessionStorage pour garder les cartes pendant toute la session
    var STORAGE_KEY = 'sortir_validated_cards';
    var SESSION_ID_KEY = 'sortir_session_id';

    // Génère ou récupère un ID de session unique pour éviter les conflits entre onglets/sessions
    var sessionId = sessionStorage.getItem(SESSION_ID_KEY);
    if (!sessionId) {
        sessionId = 'sortir_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        sessionStorage.setItem(SESSION_ID_KEY, sessionId);
    }

    // Fonction pour sauvegarder une carte validée
    function saveValidatedCard(itemKey, index, cardNumber) {
        var storageKey = STORAGE_KEY + '_' + sessionId;
        var savedCards = {};
        try {
            var stored = sessionStorage.getItem(storageKey);
            if (stored) {
                savedCards = JSON.parse(stored);
            }
        } catch (e) {
            // Erreur silencieuse - sessionStorage peut être désactivé
        }

        if (!savedCards[itemKey]) {
            savedCards[itemKey] = {};
        }
        savedCards[itemKey][index] = {
            number: cardNumber,
            timestamp: Date.now(),
            valid: true
        };

        try {
            sessionStorage.setItem(storageKey, JSON.stringify(savedCards));
        } catch (e) {
            // Erreur silencieuse - sessionStorage peut être plein
        }
    }

    // Fonction pour récupérer les cartes validées
    function getValidatedCards(itemKey) {
        var storageKey = STORAGE_KEY + '_' + sessionId;
        try {
            var stored = sessionStorage.getItem(storageKey);
            if (stored) {
                var savedCards = JSON.parse(stored);
                return savedCards[itemKey] || {};
            }
        } catch (e) {
            // Erreur silencieuse
        }
        return {};
    }

    // Fonction pour nettoyer les anciennes données (>30 minutes)
    function cleanOldSessionData() {
        var maxAge = 30 * 60 * 1000; // 30 minutes
        var now = Date.now();

        for (var i = 0; i < sessionStorage.length; i++) {
            var key = sessionStorage.key(i);
            if (key && key.startsWith(STORAGE_KEY)) {
                try {
                    var data = JSON.parse(sessionStorage.getItem(key));
                    var hasRecentData = false;

                    for (var itemKey in data) {
                        for (var index in data[itemKey]) {
                            if (data[itemKey][index].timestamp && (now - data[itemKey][index].timestamp) < maxAge) {
                                hasRecentData = true;
                                break;
                            }
                        }
                    }

                    if (!hasRecentData) {
                        sessionStorage.removeItem(key);
                    }
                } catch (e) {
                    // Supprime si données corrompues
                    sessionStorage.removeItem(key);
                }
            }
        }
    }

    // Nettoie les anciennes sessions au chargement
    cleanOldSessionData();

    // Récupère la configuration depuis l'attribut data-sortir-config
    var scriptTag = document.querySelector('script[data-sortir-config]');
    var sortirConfig = {};

    if (scriptTag && scriptTag.getAttribute('data-sortir-config')) {
        try {
            sortirConfig = JSON.parse(scriptTag.getAttribute('data-sortir-config'));
        } catch (e) {
                return;
        }
    } else {
        return;
    }

    if (!sortirConfig || Object.keys(sortirConfig).length === 0) {
        return;
    }

    // Pour chaque item Sortir, surveille les changements de quantité
    Object.keys(sortirConfig).forEach(function(itemKey) {
        var config = sortirConfig[itemKey];
        var itemId = config.item_id;

        // Trouve le sélecteur de quantité avec plusieurs stratégies
        var quantityInput = null;

        // Stratégie 1: Par ID (Pretix utilise id="item_XX")
        quantityInput = document.getElementById('item_' + itemId);

        // Stratégie 2: input par name
        if (!quantityInput) {
            quantityInput = document.querySelector('input[name="item_' + itemId + '"]');
        }

        // Stratégie 3: select
        if (!quantityInput) {
            quantityInput = document.querySelector('select[name="item_' + itemId + '"]');
        }

        // Stratégie 4: Avec variation
        if (!quantityInput && config.variation_id) {
            quantityInput = document.getElementById('item_' + itemId + '_' + config.variation_id);
        }

        if (quantityInput) {
            // Conteneur principal pour tous les champs Sortir de cet item
            var sortirFieldsContainer = document.createElement('div');
            sortirFieldsContainer.className = 'sortir-fields-container';
            sortirFieldsContainer.id = 'sortir-container-' + itemKey;

            // Insère le conteneur après le conteneur de l'item
            var container = quantityInput.closest('article, .product-row, .item-with-variations');
            if (container) {
                container.appendChild(sortirFieldsContainer);

                // Fonction helper pour créer un nouveau champ
                function createCardField(index, totalQuantity) {
                    var cardFieldId = itemKey + '_' + index;

                    var sortirField = document.createElement('div');
                    sortirField.className = 'alert alert-info sortir-field';
                    sortirField.style.marginBottom = '10px';
                    sortirField.setAttribute('data-field-index', index);

                    var title = document.createElement('h5');
                    title.textContent = 'Carte Sortir! requise (' + index + '/' + totalQuantity + ')';

                    var formGroup = document.createElement('div');
                    formGroup.className = 'form-group';

                    var label = document.createElement('label');
                    label.innerHTML = '<strong>Numéro de carte KorriGo (10 chiffres) #' + index + ':</strong>';

                    var input = document.createElement('input');
                    input.type = 'text';
                    input.className = 'form-control sortir-card-input';
                    input.id = 'sortir_card_' + cardFieldId;
                    input.placeholder = 'Ex: 1234567890';
                    input.pattern = '[0-9]{10}';
                    input.maxLength = 10;
                    input.setAttribute('data-item', itemKey);
                    input.setAttribute('data-index', index);
                    input.required = true;

                    var validationDiv = document.createElement('div');
                    validationDiv.id = 'sortir_validation_' + cardFieldId;
                    validationDiv.className = 'sortir-validation';

                    formGroup.appendChild(label);
                    formGroup.appendChild(input);
                    formGroup.appendChild(validationDiv);

                    sortirField.appendChild(title);
                    sortirField.appendChild(formGroup);

                    return sortirField;
                }

                // Fonction pour ajuster le nombre de champs selon la quantité
                function updateSortirFields() {
                    var quantity = parseInt(quantityInput.value) || 0;

                    if (quantity > 0) {
                        window.sortirValidationRequired = true;

                        // ÉTAPE 1 : SAUVEGARDE des valeurs existantes AVANT toute manipulation
                        var savedValues = {};

                        // D'abord, récupère les valeurs depuis sessionStorage (prioritaire)
                        var storedCards = getValidatedCards(itemKey);
                        for (var idx in storedCards) {
                            if (storedCards[idx] && storedCards[idx].valid) {
                                savedValues[parseInt(idx)] = {
                                    value: storedCards[idx].number,
                                    valid: 'true',
                                    validationMsg: '<i class="fa fa-check-circle"></i> Carte valide et éligible'
                                };
                            }
                        }

                        // Ensuite, check les valeurs actuelles du DOM (peuvent écraser sessionStorage si plus récentes)
                        for (var i = 1; i <= 20; i++) {  // Check jusqu'à 20
                            var cardFieldId = itemKey + '_' + i;
                            var existingInput = document.getElementById('sortir_card_' + cardFieldId);
                            if (existingInput && existingInput.value) {
                                savedValues[i] = {
                                    value: existingInput.value,
                                    valid: existingInput.getAttribute('data-valid'),
                                    validationMsg: document.getElementById('sortir_validation_' + cardFieldId)?.innerHTML || ''
                                };
                            }
                        }

                        // ÉTAPE 2 : Vérifie quels champs existent RÉELLEMENT par leur ID
                        // IMPORTANT : On vérifie TOUS les champs possibles (jusqu'à 20) pour détecter ceux à supprimer
                        var existingFieldsMap = {};
                        for (var i = 1; i <= 20; i++) {
                            var cardFieldId = itemKey + '_' + i;
                            var existingInput = document.getElementById('sortir_card_' + cardFieldId);
                            if (existingInput) {
                                existingFieldsMap[i] = existingInput.closest('.sortir-field');
                            }
                        }

                        var existingCount = Object.keys(existingFieldsMap).length;

                        // Ajoute SEULEMENT les champs manquants (entre 1 et quantity)
                        if (quantity > 0) {
                            for (var i = 1; i <= quantity; i++) {
                                if (!existingFieldsMap[i]) {
                                    // Ce champ n'existe pas, on le crée
                                    var newField = createCardField(i, quantity);
                                    sortirFieldsContainer.appendChild(newField);
                                }
                            }
                        }

                        // Supprime les champs au-delà de la quantité demandée
                        for (var i = quantity + 1; i <= 20; i++) {
                            if (existingFieldsMap[i]) {
                                // Ce champ existe mais ne devrait plus : on le supprime
                                existingFieldsMap[i].remove();
                            }
                        }

                        // ÉTAPE 3 : RESTAURATION des valeurs + mise à jour des titres
                        for (var i = 1; i <= quantity; i++) {
                            var cardFieldId = itemKey + '_' + i;
                            var input = document.getElementById('sortir_card_' + cardFieldId);
                            if (input) {
                                // Restaure les valeurs sauvegardées
                                if (savedValues[i]) {
                                    input.value = savedValues[i].value;
                                    if (savedValues[i].valid) {
                                        input.setAttribute('data-valid', savedValues[i].valid);
                                    }
                                    var validationDiv = document.getElementById('sortir_validation_' + cardFieldId);
                                    if (validationDiv && savedValues[i].validationMsg) {
                                        validationDiv.innerHTML = savedValues[i].validationMsg;
                                    }
                                }

                                // Met à jour le titre
                                var field = input.closest('.sortir-field');
                                var h5 = field ? field.querySelector('h5') : null;
                                if (h5) {
                                    h5.textContent = 'Carte Sortir! requise (' + i + '/' + quantity + ')';
                                }
                            }
                        }

                    } else {
                        // Quantité = 0 : supprime tous les champs
                        while (sortirFieldsContainer.firstChild) {
                            sortirFieldsContainer.removeChild(sortirFieldsContainer.firstChild);
                        }

                        var otherRequired = document.querySelectorAll('.sortir-card-input[required]').length > 0;
                        if (!otherRequired) {
                            window.sortirValidationRequired = false;
                        }
                    }

                    // Met à jour l'état des boutons
                    if (globalCheckSortirState) {
                        setTimeout(globalCheckSortirState, 100);
                    }
                }

                // Écoute MULTIPLE pour capturer tous les changements (Pretix peut modifier via JS)
                quantityInput.addEventListener('change', function() {
                    updateSortirFields();
                });
                quantityInput.addEventListener('input', function() {
                    updateSortirFields();
                });

                // Observer les changements de valeur via MutationObserver (si Pretix modifie l'attribut)
                var observer = new MutationObserver(function(mutations) {
                    mutations.forEach(function(mutation) {
                        if (mutation.type === 'attributes' && mutation.attributeName === 'value') {
                            updateSortirFields();
                        }
                    });
                });
                observer.observe(quantityInput, { attributes: true, attributeFilter: ['value'] });

                // Polling de secours toutes les 500ms pour détecter les changements
                var lastQuantity = parseInt(quantityInput.value) || 0;
                setInterval(function() {
                    var currentQuantity = parseInt(quantityInput.value) || 0;
                    if (currentQuantity !== lastQuantity) {
                        lastQuantity = currentQuantity;
                        updateSortirFields();
                    }
                }, 500);

                // Génération initiale
                updateSortirFields();

                // NETTOYAGE DES PENDING : Appel automatique au cleanup au chargement
                // Cela nettoie les cartes "pending" si l'utilisateur revient ou recharge la page
                setTimeout(function() {
                    var pathParts = window.location.pathname.split('/');
                    var organizer = pathParts[1];
                    var event = pathParts[2];
                    var cleanupUrl = '/' + organizer + '/' + event + '/sortir/cleanup-session/';

                    fetch(cleanupUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                        },
                        body: JSON.stringify({
                            session_id: sessionId
                        })
                    })
                    .then(function(response) {
                        return response.json();
                    })
                    .then(function(data) {
                        if (data.success && data.deleted > 0) {
                            // Nettoyage réussi
                        }
                    })
                    .catch(function(err) {
                        // Erreur lors du nettoyage
                    });
                }, 1000); // Délai pour être sûr que la page est chargée
            }
        }
    });

    // Variable globale pour la fonction de vérification des boutons
    var globalCheckSortirState = null;

    // Fonction de validation via API
    function validateCardWithAPI(cardNumber, validationDiv, input) {
        // Affiche un loading
        validationDiv.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Vérification en cours...';
        validationDiv.className = 'sortir-validation loading';
        input.setAttribute('data-valid', 'false');

        // Déclenche la vérification des boutons (mise en attente)
        if (globalCheckSortirState) {
            globalCheckSortirState();
        }

        // Récupère l'URL de base depuis l'URL actuelle
        var pathParts = window.location.pathname.split('/');
        var organizer = pathParts[1];
        var event = pathParts[2];
        var validateUrl = '/' + organizer + '/' + event + '/sortir/validate/';
        var cleanupUrl = '/' + organizer + '/' + event + '/sortir/cleanup-session/';

        // ÉTAPE 1: Nettoie d'abord les cartes "pending" de cette session avant validation
        // Cela permet de revalider une carte qu'on vient de supprimer/retaper
        var itemKey = input.dataset.item;
        var sessionId = sessionStorage.getItem(SESSION_ID_KEY);

        fetch(cleanupUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
            },
            body: JSON.stringify({
                session_id: sessionId,
                card_number: cardNumber  // Nettoie spécifiquement cette carte
            })
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(cleanupData) {
            // ÉTAPE 2: Après le cleanup, lance la validation
            return validateCardWithBackend(cardNumber, validateUrl);
        })
        .catch(function(err) {
            // Si le cleanup échoue, continue quand même avec la validation
            return validateCardWithBackend(cardNumber, validateUrl);
        })
        .then(function(data) {
            handleValidationResponse(data, cardNumber, validationDiv, input, itemKey);
        })
        .catch(function(err) {
            validationDiv.innerHTML = '<i class="fa fa-exclamation-triangle"></i> Erreur de vérification';
            validationDiv.className = 'sortir-validation error';
            input.setAttribute('data-valid', 'false');

            // Met à jour l'état des boutons même en cas d'erreur
            if (globalCheckSortirState) {
                setTimeout(globalCheckSortirState, 100);
            }
        });
    }

    // Fonction helper pour appeler l'API de validation
    function validateCardWithBackend(cardNumber, validateUrl) {
        // Récupère le session_id depuis sessionStorage (RGPD-compliant)
        var sessionId = sessionStorage.getItem(SESSION_ID_KEY) || '';

        return fetch(validateUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
            },
            body: JSON.stringify({
                card_number: cardNumber,
                session_id: sessionId  // Envoie le session_id pour gérer les corrections
            })
        })
        .then(function(response) {
            return response.json();
        });
    }

    // Fonction helper pour gérer la réponse de validation
    function handleValidationResponse(data, cardNumber, validationDiv, input, itemKey) {
        if (data.valid) {
            validationDiv.innerHTML = '<i class="fa fa-check-circle"></i> Carte valide et éligible';
            validationDiv.className = 'sortir-validation success';
            input.setAttribute('data-valid', 'true');

            // Sauvegarde le numéro validé en sessionStorage ET localement
            var index = input.dataset.index;
            saveValidatedCard(itemKey, index, cardNumber);
            saveCardToSession(cardNumber, itemKey);

            // Vérifie si toutes les cartes sont validées
            var allValid = true;
            document.querySelectorAll('.sortir-card-input[required]').forEach(function(inp) {
                if (inp.getAttribute('data-valid') !== 'true') {
                    allValid = false;
                }
            });

            if (allValid) {
                window.sortirBlockerActive = true; // Désactive le blocage global car tout est OK
            }
        } else {
            validationDiv.innerHTML = '<i class="fa fa-times-circle"></i> ' + (data.error || 'Carte non éligible');
            validationDiv.className = 'sortir-validation error';
            input.setAttribute('data-valid', 'false');
            window.sortirBlockerActive = false; // Réactive le blocage
        }

        // CRUCIAL : Met à jour l'état des boutons après validation
        if (globalCheckSortirState) {
            setTimeout(globalCheckSortirState, 100);
        }
    }

    // Fonction pour sauvegarder le numéro validé en session
    function saveCardToSession(cardNumber, itemKey) {
        // On pourrait faire un appel AJAX pour sauver en session,
        // pour l'instant on stocke juste localement
        localStorage.setItem('sortir_card_' + itemKey, cardNumber);
    }

    // Validation en temps réel pour les champs Sortir
    document.addEventListener('input', function(e) {
        if (e.target.classList.contains('sortir-card-input')) {
            var input = e.target;
            var itemKey = input.dataset.item;
            var index = input.dataset.index;
            var cardFieldId = itemKey + '_' + index;
            var validationDiv = document.getElementById('sortir_validation_' + cardFieldId);

            // Nettoie l'input (seulement chiffres)
            var cleanValue = input.value.replace(/[^0-9]/g, '');
            input.value = cleanValue;

            // Validation du format et appel API
            if (cleanValue.length === 0) {
                validationDiv.innerHTML = '';
                validationDiv.className = 'sortir-validation';
                input.setAttribute('data-valid', 'false');
            } else if (cleanValue.length < 10) {
                validationDiv.innerHTML = '<i class="fa fa-info-circle"></i> ' + (10 - cleanValue.length) + ' chiffres restants';
                validationDiv.className = 'sortir-validation text-muted';
                input.setAttribute('data-valid', 'false');
            } else if (cleanValue.length === 10) {
                // VÉRIFICATION ANTI-DOUBLON seulement au 10ème chiffre
                // Vérifie que ce numéro n'est pas déjà utilisé dans un AUTRE champ
                var allSortirInputs = document.querySelectorAll('.sortir-card-input[required]');
                var duplicateFound = false;

                allSortirInputs.forEach(function(otherInput) {
                    if (otherInput !== input && otherInput.value === cleanValue) {
                        duplicateFound = true;
                    }
                });

                if (duplicateFound) {
                    validationDiv.innerHTML = '<i class="fa fa-times-circle"></i> Ce numéro de carte est déjà utilisé dans cette commande';
                    validationDiv.className = 'sortir-validation error';
                    input.setAttribute('data-valid', 'false');
                } else {
                    // Pas de doublon : appel API automatique
                    validateCardWithAPI(cleanValue, validationDiv, input);
                }
            }

            // Met à jour l'état des boutons à chaque saisie (avec délai pour éviter surcharge)
            if (globalCheckSortirState && !window.sortirCheckPending) {
                window.sortirCheckPending = true;
                setTimeout(function() {
                    globalCheckSortirState();
                    window.sortirCheckPending = false;
                }, 200);
            }
        }
    });

    // BLOCAGE ULTRA-ROBUSTE - Désactivation complète du bouton + surveillances
    // Cherche le formulaire Pretix avec plusieurs méthodes
    var cartForm = document.querySelector('form[action*="/cart/add"]');
    if (!cartForm) {
        cartForm = document.querySelector('form[data-asynctask]');
    }
    if (!cartForm) {
        cartForm = document.querySelector('form[method="post"]');
    }


    if (cartForm) {
        // Trouve tous les boutons submit (incluant ceux sans type explicite qui sont submit par défaut)
        var submitButtons = cartForm.querySelectorAll('button[type="submit"], input[type="submit"], button:not([type]):not([data-step])');

        // Si pas de bouton trouvé dans le form, cherche après le form (Pretix met parfois le bouton à l'extérieur)
        if (submitButtons.length === 0) {
            var nextElement = cartForm.nextElementSibling;
            while (nextElement && submitButtons.length === 0) {
                if (nextElement.tagName === 'BUTTON' || (nextElement.querySelector && nextElement.querySelector('button'))) {
                    submitButtons = nextElement.querySelectorAll ? nextElement.querySelectorAll('button') : [nextElement];
                    break;
                }
                nextElement = nextElement.nextElementSibling;
            }
        }

        // Sauvegarde l'état original des boutons
        var originalButtonStates = [];
        submitButtons.forEach(function(button, index) {
            originalButtonStates[index] = {
                disabled: button.disabled,
                innerHTML: button.innerHTML,
                textContent: button.textContent,
                onclick: button.onclick,
                className: button.className
            };
        });

        // Fonction pour vérifier l'état Sortir et gérer les boutons
        function checkSortirStateAndUpdateButtons() {
            var sortirInputs = document.querySelectorAll('.sortir-card-input[required]');
            var hasError = false;
            var errorCount = 0;
            var pendingCount = 0;

            sortirInputs.forEach(function(input) {
                var itemKey = input.dataset.item;
                var value = input.value || '';
                var isValid = input.getAttribute('data-valid') === 'true';

                if (!value || value.length !== 10) {
                    hasError = true;
                    errorCount++;
                } else if (!isValid) {
                    hasError = true;
                    pendingCount++;
                }
            });

            // Gestion des boutons selon l'état
            submitButtons.forEach(function(button, index) {
                if (hasError) {
                    // DÉSACTIVE COMPLÈTEMENT le bouton
                    button.disabled = true;
                    button.style.opacity = '0.5';
                    button.style.cursor = 'not-allowed';
                    button.style.pointerEvents = 'none';

                    // Message informatif
                    var message = '';
                    if (errorCount > 0) {
                        message = 'Carte Sortir! requise';
                    } else if (pendingCount > 0) {
                        message = 'Validation Sortir! en cours...';
                    }

                    // Modifie le texte du bouton pour indiquer le problème
                    if (button.tagName === 'BUTTON') {
                        // Garde l'icône existante si elle existe
                        var existingIcon = button.querySelector('i.fa');
                        if (existingIcon) {
                            button.innerHTML = '<i class="fa fa-lock"></i> ' + message;
                        } else {
                            button.textContent = '🔒 ' + message;
                        }
                    }

                    // Ne remplace le bouton que s'il n'est pas déjà marqué comme modifié
                    if (!button.getAttribute('data-sortir-blocked')) {
                        button.setAttribute('data-sortir-blocked', 'true');

                        // Sauvegarde l'ancien onclick
                        button.setAttribute('data-original-onclick', button.onclick);

                        // Remplace le onclick au lieu de remplacer le bouton entier
                        button.onclick = function(e) {
                            e.preventDefault();
                            e.stopPropagation();
                            e.stopImmediatePropagation();
                            // Pas d'alerte, le bouton grisé suffit
                            return false;
                        };
                    }

                } else {
                    // RÉACTIVE le bouton
                    button.disabled = originalButtonStates[index].disabled;
                    button.style.opacity = '';
                    button.style.cursor = '';
                    button.style.pointerEvents = '';

                    // Marque comme non bloqué
                    button.removeAttribute('data-sortir-blocked');

                    // Restaure le texte original
                    if (originalButtonStates[index].innerHTML) {
                        button.innerHTML = originalButtonStates[index].innerHTML;
                    }
                    if (originalButtonStates[index].className) {
                        button.className = originalButtonStates[index].className;
                    }

                    // Restaure l'onclick original
                    var originalOnclick = button.getAttribute('data-original-onclick');
                    if (originalOnclick && originalOnclick !== 'null') {
                        button.onclick = Function(originalOnclick);
                    } else {
                        button.onclick = null;
                    }
                }
            });

            return !hasError;
        }

        // Assigne la fonction globale pour accès depuis validateCardWithAPI
        globalCheckSortirState = checkSortirStateAndUpdateButtons;

        // Vérifie l'état initial
        setTimeout(function() {
            checkSortirStateAndUpdateButtons();
        }, 100);

        // Surveillance continue (toutes les 2 secondes pour éviter la surcharge)
        setInterval(checkSortirStateAndUpdateButtons, 2000);

        // Blocage sur submit en dernier recours
        cartForm.addEventListener('submit', function(e) {
            if (!checkSortirStateAndUpdateButtons()) {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                // Pas d'alerte, le bouton grisé et les messages suffisent
                return false;
            }

            // Ajout des champs cachés si validation OK
            var sortirInputs = document.querySelectorAll('.sortir-card-input[required]');
            sortirInputs.forEach(function(input) {
                if (input.value && input.getAttribute('data-valid') === 'true') {
                    var itemKey = input.dataset.item;
                    var index = input.dataset.index;
                    var hiddenField = document.createElement('input');
                    hiddenField.type = 'hidden';
                    hiddenField.name = 'sortir_card_' + itemKey + '_' + index;
                    hiddenField.value = input.value;
                    cartForm.appendChild(hiddenField);
                }
            });
        }, true); // useCapture = true pour intercepter en premier

        // Observer les changements de DOM pour nouveaux boutons
        var observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) { // Element node
                        var newButtons = node.querySelectorAll ? node.querySelectorAll('button[type="submit"], input[type="submit"]') : [];
                        if (newButtons.length > 0) {
                            checkSortirStateAndUpdateButtons();
                        }
                    }
                });
            });
        });

        observer.observe(cartForm, { childList: true, subtree: true });
    } else {
        // Tente une recherche tardive (cas où le form est généré dynamiquement)
        setTimeout(function() {
            var laterForm = document.querySelector('form[action*="/cart/add"], form[data-asynctask]');
            if (laterForm) {
                window.location.reload(); // Recharge pour réinitialiser correctement
            }
        }, 2000);
    }
});
