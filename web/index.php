<div class="batterie">
    <?php
    // 1. Lecture du fichier généré par le script Python
    $data = @file_get_contents("/home/thomas/hechicero/data/batterie.txt");    
    
    if ($data) {
        // 2. On découpe les données (format : %|Etat|Couleur)
        $parts = explode("|", $data);
        
        $pourcentage = $parts[0];
        $etat = $parts[1];
        $couleur = $parts[2];
        
        // 3. Affichage avec style dynamique
        echo '<span style="color: ' . htmlspecialchars($couleur) . '; font-weight: bold;">';
        echo htmlspecialchars($etat) . ' (' . htmlspecialchars($pourcentage) . ')';
        echo '</span>';
    } else {
        echo '<span style="color: grey;">Données batterie indisponibles</span>';
    }
    ?>
</div>