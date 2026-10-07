import SharedPagination from '../../../../components/ui/Pagination'
import styles from '../../pages/articulos/VerArticulos.module.css'

const classes = { ...styles, pageInfo: styles.paginationInfo,
  pageControls: styles.paginationControls, pageBtnActive: styles.active }

export default function Pagination({ totalCount, ...props }) {
  return <SharedPagination {...props} count={totalCount} itemLabel="artículos" alwaysShow
    pageSizeLabel="Artículos por página" classes={classes} />
}
