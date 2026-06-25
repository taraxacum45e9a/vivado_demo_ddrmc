puts "[exec env]"

set proj_name "demo"
set proj_dir  "project.[pid]"
set jobs      10

# Create project
create_project $proj_name $proj_dir -part xcv80-lsva4737-2MHP-e-S
set_property board_part xilinx.com:v80:part0:1.0 [current_project]

# Import constraints
set src_dir [file dirname [file normalize [info script]]]
import_files -fileset constrs_1 -norecurse "$src_dir/../constraints/impl.pins.xdc"

# Create block design
create_bd_design "top"
create_bd_cell -type ip -vlnv xilinx.com:ip:versal_cips:3.4 versal_cips_0
apply_bd_automation -rule xilinx.com:bd_rule:cips -config { board_preset {Yes} boot_config {Custom} configure_noc {Add new AXI NoC} debug_config {JTAG} design_flow {Full System} mc_type {DDR} num_mc_ddr {2} num_mc_lpddr {None} pl_clocks {None} pl_resets {None}}  [get_bd_cells versal_cips_0]
save_bd_design
validate_bd_design

add_files -norecurse [make_wrapper -files [get_files "top.bd"] -top]
update_compile_order -fileset sources_1

############################################################

proc get_ddrmc_elfs {} {
  set ddrmc_elfs {}
  foreach elf [get_files -quiet "*ddrmc.elf"] {
    lappend ddrmc_elfs [file normalize $elf]
  }
  return $ddrmc_elfs
}

proc find_missing_files {filelist} {
  set missing {}
  foreach fpath $filelist {
    if {![file exists $fpath]} {
      lappend missing $fpath
    }
  }
  return $missing
}

# Ensure top BD is generated
generate_target all [get_files "top.bd"]

# Check for missing DDRMC ELF files before proceeding
puts "INFO: Checking for DDRMC ELF files..."
set ddrmc_elfs [get_ddrmc_elfs]
set missing_elfs [find_missing_files $ddrmc_elfs]
if {[llength $missing_elfs] > 0} {
  puts "ERROR: DDRMC output product generation did not physically produce the ELF files."
  puts "Try: reset/regenerate BD/IP output products, then inspect IP generation logs."
  error "DDRMC ELF missing on disk: $missing_elfs"
} else {
  puts "INFO: All DDRMC ELF files are present: $ddrmc_elfs"
  exit 0
}
