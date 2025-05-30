/**
 * This script handles the dynamic form generation with dropdown menus
 * Add this to your index.html file or include as a separate JS file
 */

function generateFormSection(sectionName, sectionFields, data) {
    const section = document.createElement('div');
    section.className = 'form-section';
    
    // Format section name for display
    const formattedName = sectionName.charAt(0).toUpperCase() + sectionName.slice(1).replace('_', ' ');
    
    section.innerHTML = `<h4>${formattedName}</h4>`;
    
    // Create fields
    const fieldsContainer = document.createElement('div');
    fieldsContainer.className = 'row';
    
    sectionFields.forEach(field => {
        const fieldValue = data && data[sectionName] ? data[sectionName][field.name] || '' : '';
        
        const fieldCol = document.createElement('div');
        fieldCol.className = 'col-md-6 mb-3';
        
        let labelClass = 'form-label';
        if (field.required) {
            labelClass += ' required-field';
        }
        
        let fieldHtml = `<label for="${sectionName}_${field.name}" class="${labelClass}">${field.label}:</label>`;
        
        // Check if field has a specific type (like select)
        if (field.type === 'select' && field.options) {
            fieldHtml += `
                <select class="form-select${field.required ? ' highlight-field' : ''}" 
                       id="${sectionName}_${field.name}" 
                       name="${sectionName}.${field.name}" 
                       ${field.required ? 'required' : ''}>
                    <option value="">Seleccione...</option>
            `;
            
            field.options.forEach(option => {
                const optionValue = typeof option === 'object' ? option.value || option.code : option;
                const optionLabel = typeof option === 'object' ? option.label || option.name : option;
                const selected = fieldValue === optionValue ? 'selected' : '';
                
                fieldHtml += `<option value="${optionValue}" ${selected}>${optionLabel}</option>`;
            });
            
            fieldHtml += `</select>`;
        } else {
            // Regular text input
            fieldHtml += `
                <input type="text" class="form-control${field.required ? ' highlight-field' : ''}" 
                       id="${sectionName}_${field.name}" 
                       name="${sectionName}.${field.name}" 
                       value="${fieldValue}" 
                       ${field.required ? 'required' : ''}>
            `;
        }
        
        fieldCol.innerHTML = fieldHtml;
        fieldsContainer.appendChild(fieldCol);
    });
    
    section.appendChild(fieldsContainer);
    return section;
}

// Function to fill form with suggested data
function fillFormWithData(data, requiredFields) {
    const formSections = document.getElementById('formSections');
    formSections.innerHTML = '';
    
    // Generate form sections based on required fields
    for (const [section, fields] of Object.entries(requiredFields)) {
        const sectionElement = generateFormSection(section, fields, data);
        formSections.appendChild(sectionElement);
    }
    
    // Show the form
    document.getElementById('dataForm').style.display = 'block';
}
