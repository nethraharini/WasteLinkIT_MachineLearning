// Form Submission Logic for Estimated Availability
document.getElementById("estimateForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    
    // Gather form data
    const formData = new FormData(this);
    const data = Object.fromEntries(formData.entries());
    
    // Convert appropriate fields to correct data types
    data.estimated_quantity = parseInt(data.estimated_quantity);
    data.year = parseInt(data.year);
    
    // Send the POST request to the backend
    const res = await fetch("/api/availability", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
    
    const result = await res.json();
    if (res.ok) {
      alert(result.message);  // Success message
    } else {
      alert("Error: " + result.message);  // Error message
    }
    
    // Reset the form fields after submission
    this.reset();
  });
  
  // Form Submission Logic for Confirming Actual Quantity
document.getElementById("confirmForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    
    // Gather form data
    const formData = new FormData(this);
    const data = Object.fromEntries(formData.entries());
    
    // Convert appropriate fields to correct data types
    data.confirmed_quantity = parseInt(data.confirmed_quantity);
    data.year = parseInt(data.year);
    
    // Send the PUT request to the backend to confirm the quantity
    const res = await fetch("/api/availability/confirm", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
    
    const result = await res.json();
    if (res.ok) {
      alert(result.message);  // Success message
    } else {
      alert("Error: " + result.message);  // Error message
    }
    
    // Reset the form fields after submission
    this.reset();
  });
  
  // Tab Switching Logic for Producer Dashboard
  const buttons = document.querySelectorAll(".menu-btn");
  const sections = document.querySelectorAll(".form-section");
  
  // Log buttons and sections for debugging
  console.log("Buttons:", buttons);
  console.log("Sections:", sections);
  
  // Loop through each button and add event listener to switch tabs
  buttons.forEach(btn => {
    btn.addEventListener("click", () => {
      // Remove 'active' class from all buttons and sections
      buttons.forEach(b => b.classList.remove("active"));
      sections.forEach(s => s.classList.remove("active"));
      
      // Add 'active' class to clicked button and corresponding section
      btn.classList.add("active");
      const targetSection = document.getElementById(btn.dataset.target);
      if (targetSection) {
        targetSection.classList.add("active");
      } else {
        console.error(`Section with ID ${btn.dataset.target} not found.`);
      }
    });
  });
  